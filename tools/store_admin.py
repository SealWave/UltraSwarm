"""
tools/store_admin.py
====================
E-commerce store admin automation tool.
Supports Shopify, WooCommerce, and generic admin portals.
Agents use this as a "superpower" to create/update products directly.
"""

import os
import json
import requests
from typing import Optional
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()
console = Console()

STORE_URL = os.getenv("STORE_URL", "")
STORE_ADMIN = os.getenv("STORE_ADMIN_URL", "")
STORE_USER = os.getenv("STORE_ADMIN_USER", "")
STORE_PASS = os.getenv("STORE_ADMIN_PASS", "")


def normalize_product_for_handoff(product_data: dict) -> dict:
    """Normalize product data from agents before store/admin upload."""
    title = (
        product_data.get("product_name")
        or product_data.get("title")
        or product_data.get("name")
        or ""
    )
    description = (
        product_data.get("description")
        or product_data.get("description_html")
        or product_data.get("body_html")
        or product_data.get("short_description")
        or ""
    )
    tags = product_data.get("tags", [])
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

    return {
        **product_data,
        "product_name": str(title).strip(),
        "description": str(description).strip(),
        "category": product_data.get("category") or product_data.get("product_type") or "",
        "tags": tags,
        "price": str(product_data.get("price") or product_data.get("regular_price") or "0.00"),
        "source_url": product_data.get("source_url", ""),
        "rating": product_data.get("rating", ""),
        "order_count": product_data.get("order_count", 0),
        "review_count": product_data.get("review_count", 0),
    }


def validate_product_for_upload(product_data: dict) -> tuple[bool, list[str]]:
    """Return whether required upload fields are present."""
    normalized = normalize_product_for_handoff(product_data)
    required = ["product_name", "description", "price"]
    missing = [field for field in required if not str(normalized.get(field, "")).strip()]
    return not missing, missing


class ShopifyAdmin:
    """Shopify REST Admin API client."""

    def __init__(self, shop_url: str, access_token: str):
        self.base = f"https://{shop_url}/admin/api/2024-01"
        self.headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json",
        }

    def create_product(self, data: dict) -> dict:
        """
        Create a new product.
        data = {title, body_html, vendor, product_type, tags, variants:[{price}], images}
        """
        resp = requests.post(
            f"{self.base}/products.json",
            headers=self.headers,
            json={"product": data},
            timeout=30,
        )
        return resp.json()

    def update_product(self, product_id: str, data: dict) -> dict:
        resp = requests.put(
            f"{self.base}/products/{product_id}.json",
            headers=self.headers,
            json={"product": data},
            timeout=30,
        )
        return resp.json()

    def get_products(self, limit: int = 50) -> list:
        resp = requests.get(
            f"{self.base}/products.json?limit={limit}",
            headers=self.headers,
            timeout=30,
        )
        return resp.json().get("products", [])

    def create_blog_post(self, title: str, body_html: str, tags: str = "") -> dict:
        resp = requests.post(
            f"{self.base}/blogs/news/articles.json",
            headers=self.headers,
            json={"article": {"title": title, "body_html": body_html, "tags": tags}},
            timeout=30,
        )
        return resp.json()

    def update_metafield(self, product_id: str, key: str, value: str) -> dict:
        """Update SEO metafields (meta title, description)."""
        resp = requests.post(
            f"{self.base}/products/{product_id}/metafields.json",
            headers=self.headers,
            json={"metafield": {
                "namespace": "seo",
                "key": key,
                "value": value,
                "type": "single_line_text_field",
            }},
            timeout=30,
        )
        return resp.json()


class WooCommerceAdmin:
    """WooCommerce REST API client."""

    def __init__(self, store_url: str, consumer_key: str, consumer_secret: str):
        self.base = f"{store_url}/wp-json/wc/v3"
        self.auth = (consumer_key, consumer_secret)

    def create_product(self, data: dict) -> dict:
        resp = requests.post(
            f"{self.base}/products",
            auth=self.auth,
            json=data,
            timeout=30,
        )
        return resp.json()

    def get_products(self, per_page: int = 50) -> list:
        resp = requests.get(
            f"{self.base}/products?per_page={per_page}",
            auth=self.auth,
            timeout=30,
        )
        return resp.json()

    def update_product(self, product_id: int, data: dict) -> dict:
        resp = requests.put(
            f"{self.base}/products/{product_id}",
            auth=self.auth,
            json=data,
            timeout=30,
        )
        return resp.json()

    def create_coupon(self, code: str, discount_type: str, amount: str) -> dict:
        resp = requests.post(
            f"{self.base}/coupons",
            auth=self.auth,
            json={"code": code, "discount_type": discount_type, "amount": amount},
            timeout=30,
        )
        return resp.json()


def format_product_for_store(agent_output: dict, platform: str = "shopify") -> dict:
    """
    Convert agent-generated product data into store-ready format.
    """
    agent_output = normalize_product_for_handoff(agent_output)
    if platform == "shopify":
        return {
            "title": agent_output.get("product_name", ""),
            "body_html": agent_output.get("description_html", agent_output.get("description", "")),
            "vendor": agent_output.get("brand", os.getenv("STORE_NAME", "")),
            "product_type": agent_output.get("category", ""),
            "tags": ",".join(agent_output.get("tags", [])) if isinstance(agent_output.get("tags"), list) else agent_output.get("tags", ""),
            "variants": [{"price": str(agent_output.get("price", "0.00"))}],
        }
    elif platform == "woocommerce":
        return {
            "name": agent_output.get("product_name", ""),
            "type": "simple",
            "regular_price": str(agent_output.get("price", "0.00")),
            "description": agent_output.get("description", ""),
            "short_description": agent_output.get("short_description", ""),
            "categories": [{"name": agent_output.get("category", "")}],
            "tags": [{"name": t} for t in agent_output.get("tags", [])] if isinstance(agent_output.get("tags"), list) else [],
        }
    return agent_output


def create_product_via_browser(product_data: dict) -> dict:
    """
    Automate product creation by logging into the store admin page via browser.
    """
    import re
    import time
    from tools.browser import AgentBrowser

    admin_url = os.getenv("STORE_ADMIN_URL", "")
    username = os.getenv("STORE_ADMIN_USER", "")
    password = os.getenv("STORE_ADMIN_PASS", "")
    
    if not admin_url or not username or not password:
        return {"success": False, "error": "Admin credentials or URL not configured in .env"}
        
    console.print(f"[dim]  -> Starting browser admin automation at: {admin_url}[/dim]")
    
    # 1. Open admin login page
    page = AgentBrowser.fetch_page(admin_url)
    snapshot = page.get("text", "")
    
    user_ref = None
    pass_ref = None
    submit_ref = None
    
    for line in snapshot.split("\n"):
        if ("textbox" in line or "input" in line) and any(kw in line.lower() for kw in ["user", "email", "login"]):
            match = re.search(r"@e\d+", line)
            if match:
                user_ref = match.group(0)
        if ("password" in line or "input" in line) and "password" in line.lower():
            match = re.search(r"@e\d+", line)
            if match:
                pass_ref = match.group(0)
        if ("button" in line or "submit" in line) and any(kw in line.lower() for kw in ["log", "submit", "enter", "sign"]):
            match = re.search(r"@e\d+", line)
            if match:
                submit_ref = match.group(0)
                
    if user_ref and pass_ref:
        console.print(f"[dim]  -> Found credentials inputs. Logging in...[/dim]")
        AgentBrowser.type_text(user_ref, username)
        AgentBrowser.type_text(pass_ref, password)
        if submit_ref:
            AgentBrowser.click(submit_ref)
        time.sleep(5)
        
    # 2. Go to Add Product page
    add_product_url = ""
    if "wp-admin" in admin_url or "wp-login" in admin_url:
        add_product_url = admin_url.split("/wp-")[0] + "/wp-admin/post-new.php?post_type=product"
    else:
        add_product_url = admin_url.rstrip("/") + "/products/new"
        
    console.print(f"[dim]  -> Opening add product page: {add_product_url}[/dim]")
    page = AgentBrowser.fetch_page(add_product_url)
    snapshot = page.get("text", "")
    
    title_ref = None
    desc_ref = None
    price_ref = None
    publish_ref = None
    
    for line in snapshot.split("\n"):
        if "textbox" in line and any(kw in line.lower() for kw in ["title", "name"]):
            match = re.search(r"@e\d+", line)
            if match:
                title_ref = match.group(0)
        if "textbox" in line and any(kw in line.lower() for kw in ["description", "content", "body"]):
            match = re.search(r"@e\d+", line)
            if match:
                desc_ref = match.group(0)
        if "textbox" in line and any(kw in line.lower() for kw in ["price", "regular price", "amount"]):
            match = re.search(r"@e\d+", line)
            if match:
                price_ref = match.group(0)
        if "button" in line and any(kw in line.lower() for kw in ["publish", "save", "create", "submit"]):
            match = re.search(r"@e\d+", line)
            if match:
                publish_ref = match.group(0)
                
    if title_ref:
        AgentBrowser.type_text(title_ref, product_data.get("product_name", ""))
    if desc_ref:
        AgentBrowser.type_text(desc_ref, product_data.get("description", ""))
    if price_ref:
        AgentBrowser.type_text(price_ref, str(product_data.get("price", "0.00")))
        
    if publish_ref:
        console.print(f"[dim]  -> Saving product via browser...[/dim]")
        AgentBrowser.click(publish_ref)
        return {"success": True, "method": "browser_automation", "status": "pushed"}
        
    return {"success": False, "error": "Could not locate product entry fields on admin page"}
