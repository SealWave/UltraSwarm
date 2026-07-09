"""
agents/fiverr/scraping_lead_gen_agent.py
==========================================
Scraping_Lead_Gen_Agent — web scraping and lead generation order fulfillment.

Responsibilities:
1. Parse the task instruction to extract data_type, target_source, and
   requested_quantity.
2. Use google_search() to find source URLs when the target is a category string.
3. Use scrapling (Fetcher/StealthyFetcher) to retrieve and extract records from
   source URLs (max 10 pages per URL).
4. Clean collected records: dedup, email validation, primary-identifier check.
5. Retry up to 3 additional google_search() queries when the record count is
   below requested_quantity.
6. Return status="partial" + available records when the target cannot be met.
7. Save the collected dataset via tools/output_manager.save_output(format="json").
8. On save exception: log it, set status="error", preserve data — never re-raise.
9. Include delivery_summary (50-500 chars) and context_for_next in the result.

Pattern: standalone class (same style as GigCreationAgent), NOT a subclass of
BaseAgent. LLM access via core.make_client(); scraping via scrapling library.

Usage:
    from agents.fiverr.scraping_lead_gen_agent import ScrapingLeadGenAgent

    agent = ScrapingLeadGenAgent()
    result = agent.run({
        "instruction": "Scrape 50 business emails from NY restaurants",
        "context": {}
    })
"""

from __future__ import annotations

import os
import re
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from rich.console import Console

from core import make_client
from tools.browser import google_search
from tools.output_manager import save_output

console = Console()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Supported data types and their primary identifier field (requirement 4.1, 4.4)
_DATA_TYPE_PRIMARY_ID: dict[str, str] = {
    "emails": "email",
    "contacts": "full_name",
    "business_listings": "business_name",
    "urls": "url",
}

# Email validation regex (requirement 4.4)
_EMAIL_PATTERN = re.compile(r"[^@]+@[^@]+\.[^@]+")

# Maximum pages to fetch per source URL (requirement 4.2)
_MAX_PAGES_PER_URL = 10

# Maximum additional google_search() retries (requirement 4.6)
_MAX_EXTRA_SEARCHES = 3

_SYSTEM_PROMPT = """
You are a data extraction specialist. When given raw page text you extract
structured records of the requested data type.

Return ONLY a JSON array of objects. Each object must have the fields
appropriate for the requested data type:
- emails: {"email": "...", "name": "...", "source": "..."}
- contacts: {"full_name": "...", "email": "...", "phone": "...", "company": "...", "source": "..."}
- business_listings: {"business_name": "...", "address": "...", "phone": "...", "website": "...", "source": "..."}
- urls: {"url": "...", "title": "...", "description": "...", "source": "..."}

Rules:
- Return ONLY valid JSON array. No markdown, no preamble.
- Include as many records as you can find in the text.
- For emails data type, only include records that have a valid email address.
- For missing fields use empty string "".
"""


class ScrapingLeadGenAgent:
    """
    Fiverr Scraping & Lead Generation Agent.

    Fulfils client orders that require web scraping or lead generation by
    searching for source URLs, extracting structured records with scrapling,
    cleaning and deduplicating the data, and returning it in a standardised
    result dict.

    Compatible with the FiverrManager agent registry interface.
    """

    name = "scraping_lead_gen_agent"
    role = "worker"
    description = (
        "Fulfils Fiverr client orders for web scraping and lead generation. "
        "Searches for target data sources via google_search(), scrapes pages "
        "with scrapling, cleans/deduplicates records, and returns structured "
        "data with delivery context."
    )
    skills = ["web_scraping_skill", "lead_generation_skill"]

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self.client = make_client(_SYSTEM_PROMPT, "SCRAPING-LEAD-GEN")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_metadata(self) -> dict:
        """Return agent metadata compatible with the FiverrManager registry."""
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "skills": self.skills,
        }

    def run(self, input_data: dict) -> dict:
        """Main entry-point for the Scraping Lead Gen Agent.

        Parameters
        ----------
        input_data : dict
            Accepted keys:
            - ``"instruction"`` (str): task description with data_type,
              target_source, and requested_quantity.
            - ``"context"`` (dict): optional shared state from FiverrManager.
            - ``"task_id"`` (str): optional task identifier for logging.

        Returns
        -------
        dict
            AgentResult-compatible dict with keys:
            ``status``, ``message``, ``data``, ``context_for_next``.
        """
        task_id = input_data.get("task_id", "scraping_task")
        instruction = input_data.get("instruction", "")
        context = input_data.get("context", {})

        console.print(
            f"[bold blue][ScrapingLeadGenAgent][/bold blue] "
            f"Starting task {task_id}"
        )

        try:
            return self._run_pipeline(task_id, instruction, context)
        except Exception as exc:
            tb = traceback.format_exc()
            console.print(
                f"[bold blue][ScrapingLeadGenAgent][/bold blue] "
                f"[red]Unhandled exception: {exc}[/red]"
            )
            return {
                "status": "error",
                "message": f"ScrapingLeadGenAgent encountered an unexpected error: {exc}",
                "data": {"traceback": tb},
                "context_for_next": {"record_count": 0, "data_type": ""},
            }

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------

    def _run_pipeline(self, task_id: str, instruction: str, context: dict) -> dict:
        """Execute the full scraping/lead-gen pipeline.

        Steps
        -----
        1. Parse instruction → data_type, target_source, requested_quantity.
        2. Resolve source URLs (direct URL or google_search category).
        3. Scrape pages with scrapling (max 10 pages per URL).
        4. Clean records (dedup, email validation, primary ID check).
        5. Retry up to 3 more searches if count < requested_quantity.
        6. Save output; handle save exceptions gracefully.
        7. Return result dict with context_for_next.
        """
        # ── Step 1: Parse instruction ──────────────────────────────────
        parsed = self._parse_instruction(instruction)
        data_type = parsed.get("data_type", "emails")
        target_source = parsed.get("target_source", "")
        requested_quantity = parsed.get("requested_quantity", 10)

        if data_type not in _DATA_TYPE_PRIMARY_ID:
            data_type = "emails"

        console.print(
            f"[bold blue][ScrapingLeadGenAgent][/bold blue] "
            f"data_type={data_type}, target_source={target_source}, "
            f"requested_quantity={requested_quantity}"
        )

        primary_id_field = _DATA_TYPE_PRIMARY_ID[data_type]

        # ── Step 2: Resolve source URLs ────────────────────────────────
        source_urls = self._resolve_source_urls(target_source, data_type)
        primary_source = target_source or "google search"

        # ── Step 3: Scrape pages ───────────────────────────────────────
        all_records: list[dict] = []
        for url in source_urls:
            records = self._scrape_url(url, data_type)
            all_records.extend(records)

        # ── Step 4: Clean records ──────────────────────────────────────
        cleaned = self._clean_records(all_records, data_type, primary_id_field)
        console.print(
            f"[bold blue][ScrapingLeadGenAgent][/bold blue] "
            f"After initial scrape: {len(cleaned)} clean records"
        )

        # ── Step 5: Retry searches if insufficient ─────────────────────
        extra_searches = 0
        while len(cleaned) < requested_quantity and extra_searches < _MAX_EXTRA_SEARCHES:
            extra_searches += 1
            console.print(
                f"[bold blue][ScrapingLeadGenAgent][/bold blue] "
                f"Extra search attempt {extra_searches}/{_MAX_EXTRA_SEARCHES} "
                f"({len(cleaned)}/{requested_quantity} records so far)"
            )
            extra_urls = self._retry_search(target_source, data_type, extra_searches)
            for url in extra_urls:
                records = self._scrape_url(url, data_type)
                all_records.extend(records)
            cleaned = self._clean_records(all_records, data_type, primary_id_field)
            console.print(
                f"[bold blue][ScrapingLeadGenAgent][/bold blue] "
                f"After extra search {extra_searches}: {len(cleaned)} clean records"
            )

        record_count = len(cleaned)
        status = "success" if record_count >= requested_quantity else "partial"

        # ── Step 6: Build delivery summary (req 4.9) ───────────────────
        delivery_summary = self._build_delivery_summary(
            data_type, record_count, primary_source, requested_quantity
        )

        # ── Step 7: Save output (req 4.7, 4.8) ────────────────────────
        save_data = {
            "data_type": data_type,
            "requested_quantity": requested_quantity,
            "record_count": record_count,
            "primary_source": primary_source,
            "records": cleaned,
            "delivery_summary": delivery_summary,
        }
        try:
            save_output("scraping_lead_gen_agent", "lead_data", save_data, "json")
        except Exception as save_exc:
            console.print(
                f"[bold blue][ScrapingLeadGenAgent][/bold blue] "
                f"[red]Save failed: {save_exc}[/red]"
            )
            return {
                "status": "error",
                "message": f"Data collected but save failed: {save_exc}",
                "data": {
                    "records": cleaned,
                    "record_count": record_count,
                    "data_type": data_type,
                    "delivery_summary": delivery_summary,
                    "save_error": str(save_exc),
                },
                "context_for_next": {
                    "record_count": record_count,
                    "data_type": data_type,
                },
            }

        # ── Step 8: Return result ──────────────────────────────────────
        msg = (
            f"Collected {record_count} {data_type} records"
            + (f" (partial — requested {requested_quantity})" if status == "partial" else "")
            + f" from {primary_source}."
        )
        console.print(
            f"[bold blue][ScrapingLeadGenAgent][/bold blue] "
            f"{msg} Status: {status}"
        )
        return {
            "status": status,
            "message": msg,
            "data": {
                "records": cleaned,
                "record_count": record_count,
                "data_type": data_type,
                "delivery_summary": delivery_summary,
            },
            "context_for_next": {
                "record_count": record_count,
                "data_type": data_type,
            },
        }

    # ------------------------------------------------------------------
    # Instruction parsing
    # ------------------------------------------------------------------

    def _parse_instruction(self, instruction: str) -> dict:
        """Use the LLM to extract structured parameters from the instruction.

        Returns a dict with keys: data_type, target_source, requested_quantity.
        Falls back to safe defaults if parsing fails.
        """
        if not instruction.strip():
            return {"data_type": "emails", "target_source": "", "requested_quantity": 10}

        prompt = (
            f"Extract the following from this task instruction and return as JSON:\n\n"
            f"Instruction: {instruction}\n\n"
            f"Extract:\n"
            f"- data_type: one of 'emails', 'contacts', 'business_listings', 'urls'\n"
            f"- target_source: a website URL or business category string\n"
            f"- requested_quantity: a positive integer (default 10 if not specified)\n\n"
            f"Return ONLY JSON with these three keys."
        )
        result = self.client.ask_json(prompt)

        if not isinstance(result, dict) or result.get("parse_error"):
            # Fallback: try basic regex extraction
            return self._parse_instruction_regex(instruction)

        data_type = result.get("data_type", "emails")
        if data_type not in _DATA_TYPE_PRIMARY_ID:
            data_type = "emails"

        try:
            quantity = int(result.get("requested_quantity", 10))
            if quantity <= 0:
                quantity = 10
        except (TypeError, ValueError):
            quantity = 10

        return {
            "data_type": data_type,
            "target_source": str(result.get("target_source", "")).strip(),
            "requested_quantity": quantity,
        }

    def _parse_instruction_regex(self, instruction: str) -> dict:
        """Regex-based fallback parser for task instructions."""
        lower = instruction.lower()

        # Detect data type
        data_type = "emails"
        for dt in _DATA_TYPE_PRIMARY_ID:
            if dt.replace("_", " ") in lower or dt in lower:
                data_type = dt
                break

        # Detect quantity
        quantity = 10
        qty_match = re.search(r"\b(\d+)\b", instruction)
        if qty_match:
            try:
                quantity = max(1, int(qty_match.group(1)))
            except ValueError:
                pass

        # Detect URL
        url_match = re.search(r"https?://\S+", instruction)
        target_source = url_match.group(0) if url_match else ""

        # If no URL, use the instruction itself as category hint
        if not target_source:
            # Strip common lead words to get the category
            for noise in ["scrape", "collect", "find", "get", "extract",
                          "generate", str(quantity), data_type.replace("_", " ")]:
                lower = lower.replace(noise, "")
            target_source = lower.strip(" .,;:")[:100]

        return {
            "data_type": data_type,
            "target_source": target_source,
            "requested_quantity": quantity,
        }

    # ------------------------------------------------------------------
    # URL resolution
    # ------------------------------------------------------------------

    def _resolve_source_urls(self, target_source: str, data_type: str) -> list[str]:
        """Resolve target_source to a list of URLs to scrape.

        If target_source is already a URL, return it in a list.
        Otherwise treat it as a category and run google_search().
        """
        if re.match(r"https?://", target_source.strip()):
            return [target_source.strip()]

        # Category string — use google_search (requirement 4.3)
        query = f"{target_source} {data_type.replace('_', ' ')} list"
        console.print(
            f"[bold blue][ScrapingLeadGenAgent][/bold blue] "
            f"Searching for source URLs: {query}"
        )
        try:
            search_results = google_search(query)
        except Exception as exc:
            console.print(
                f"[bold blue][ScrapingLeadGenAgent][/bold blue] "
                f"[yellow]Search failed: {exc}[/yellow]"
            )
            return []

        urls = [r.get("url", "") for r in search_results if r.get("url")]
        console.print(
            f"[bold blue][ScrapingLeadGenAgent][/bold blue] "
            f"Found {len(urls)} source URLs"
        )
        return urls[:8]  # cap initial batch

    def _retry_search(self, target_source: str, data_type: str, attempt: int) -> list[str]:
        """Generate an alternative search query for extra scraping attempts."""
        variations = [
            f"{target_source} {data_type.replace('_', ' ')} directory",
            f"{target_source} contact {data_type.replace('_', ' ')} database",
            f"free {data_type.replace('_', ' ')} list {target_source}",
        ]
        query = variations[(attempt - 1) % len(variations)]
        console.print(
            f"[bold blue][ScrapingLeadGenAgent][/bold blue] "
            f"Retry search query: {query}"
        )
        try:
            results = google_search(query)
        except Exception as exc:
            console.print(
                f"[bold blue][ScrapingLeadGenAgent][/bold blue] "
                f"[yellow]Retry search failed: {exc}[/yellow]"
            )
            return []
        return [r.get("url", "") for r in results if r.get("url")][:5]

    # ------------------------------------------------------------------
    # Scraping (scrapling)
    # ------------------------------------------------------------------

    def _scrape_url(self, url: str, data_type: str) -> list[dict]:
        """Fetch and extract records from *url* using scrapling.

        Fetches up to _MAX_PAGES_PER_URL pages (following pagination or
        incrementing page query params). Uses StealthyFetcher for dynamic
        sites and falls back to Fetcher for static ones.

        Parameters
        ----------
        url : str
            Source URL to scrape.
        data_type : str
            Type of records to extract.

        Returns
        -------
        list[dict]
            Raw (uncleaned) records extracted from the page(s).
        """
        if not url or not url.startswith("http"):
            return []

        records: list[dict] = []
        pages_fetched = 0

        console.print(
            f"[bold blue][ScrapingLeadGenAgent][/bold blue] "
            f"Scraping: {url}"
        )

        current_url = url
        visited_urls: set[str] = set()

        while pages_fetched < _MAX_PAGES_PER_URL and current_url not in visited_urls:
            visited_urls.add(current_url)
            page_text = self._fetch_with_scrapling(current_url)

            if not page_text:
                break

            # Extract records from page text via LLM
            page_records = self._extract_records_from_text(
                page_text, data_type, current_url
            )
            records.extend(page_records)
            pages_fetched += 1

            console.print(
                f"[bold blue][ScrapingLeadGenAgent][/bold blue] "
                f"  Page {pages_fetched}: extracted {len(page_records)} records "
                f"(total: {len(records)})"
            )

            # Try to find next page URL
            next_url = self._find_next_page_url(current_url, pages_fetched)
            if not next_url or next_url == current_url:
                break
            current_url = next_url

        return records

    def _fetch_with_scrapling(self, url: str) -> str:
        """Fetch page content using scrapling library.

        Tries StealthyFetcher first (handles JS-heavy sites), then falls back
        to the plain Fetcher for static pages.

        Returns
        -------
        str
            Extracted text content, or empty string on failure.
        """
        try:
            from scrapling import StealthyFetcher, Fetcher
        except ImportError:
            console.print(
                "[bold blue][ScrapingLeadGenAgent][/bold blue] "
                "[yellow]scrapling not installed — falling back to requests[/yellow]"
            )
            return self._fetch_with_requests(url)

        # Try StealthyFetcher first
        try:
            page = StealthyFetcher.fetch(url, headless=True, network_idle=True)
            if page and page.text:
                return self._clean_html_text(page.text)
        except Exception as exc:
            console.print(
                f"[bold blue][ScrapingLeadGenAgent][/bold blue] "
                f"[dim]StealthyFetcher failed for {url}: {exc} — trying Fetcher[/dim]"
            )

        # Fallback: plain Fetcher
        try:
            page = Fetcher.fetch(url)
            if page and page.text:
                return self._clean_html_text(page.text)
        except Exception as exc:
            console.print(
                f"[bold blue][ScrapingLeadGenAgent][/bold blue] "
                f"[yellow]Fetcher also failed for {url}: {exc}[/yellow]"
            )

        return ""

    def _fetch_with_requests(self, url: str) -> str:
        """Basic HTTP fallback when scrapling is unavailable."""
        import requests as _requests
        try:
            resp = _requests.get(url, timeout=15, headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/125.0 Safari/537.36"
                )
            })
            resp.raise_for_status()
            return self._clean_html_text(resp.text)
        except Exception as exc:
            console.print(
                f"[bold blue][ScrapingLeadGenAgent][/bold blue] "
                f"[yellow]requests fallback failed for {url}: {exc}[/yellow]"
            )
            return ""

    @staticmethod
    def _clean_html_text(html: str) -> str:
        """Strip HTML tags and collapse whitespace. Returns first 8000 chars."""
        text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:8000]

    @staticmethod
    def _find_next_page_url(base_url: str, current_page: int) -> str:
        """Generate a candidate next-page URL by appending/incrementing page param."""
        if "page=" in base_url:
            return re.sub(r"page=\d+", f"page={current_page + 1}", base_url)
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}page={current_page + 1}"

    # ------------------------------------------------------------------
    # Record extraction via LLM
    # ------------------------------------------------------------------

    def _extract_records_from_text(
        self, text: str, data_type: str, source_url: str
    ) -> list[dict]:
        """Use the LLM to extract structured records from raw page text.

        Parameters
        ----------
        text : str
            Cleaned page text (max 8000 chars).
        data_type : str
            Target data type (emails, contacts, business_listings, urls).
        source_url : str
            Source URL for provenance tracking.

        Returns
        -------
        list[dict]
            List of extracted record dicts (may be empty).
        """
        if not text.strip():
            return []

        prompt = (
            f"Extract all {data_type.replace('_', ' ')} records from the following "
            f"web page text. Source URL: {source_url}\n\n"
            f"Page text:\n{text[:6000]}\n\n"
            f"Return a JSON array of records. If none found, return []."
        )

        try:
            result = self.client.ask_json(prompt)
        except Exception as exc:
            console.print(
                f"[bold blue][ScrapingLeadGenAgent][/bold blue] "
                f"[yellow]LLM extraction failed: {exc}[/yellow]"
            )
            return []

        if isinstance(result, list):
            # Tag each record with the source URL if missing
            for rec in result:
                if isinstance(rec, dict) and not rec.get("source"):
                    rec["source"] = source_url
            return result

        # The LLM sometimes wraps the array in a dict
        if isinstance(result, dict) and not result.get("parse_error"):
            for key in ("records", "data", "results", "items"):
                if isinstance(result.get(key), list):
                    items = result[key]
                    for rec in items:
                        if isinstance(rec, dict) and not rec.get("source"):
                            rec["source"] = source_url
                    return items

        return []

    # ------------------------------------------------------------------
    # Data cleaning
    # ------------------------------------------------------------------

    def _clean_records(
        self,
        records: list[dict],
        data_type: str,
        primary_id_field: str,
    ) -> list[dict]:
        """Clean, deduplicate, and validate raw records.

        Steps:
        1. Remove non-dict items.
        2. Validate primary identifier is present and non-empty.
        3. For emails data type: validate email format.
        4. Deduplicate by primary identifier value (case-insensitive).

        Parameters
        ----------
        records : list[dict]
            Raw records from scraping.
        data_type : str
            The data type being collected.
        primary_id_field : str
            The field name that must be non-empty.

        Returns
        -------
        list[dict]
            Cleaned, deduplicated records.
        """
        seen: set[str] = set()
        cleaned: list[dict] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            primary_val = str(rec.get(primary_id_field, "")).strip()

            # Remove records missing their primary identifier (req 4.4)
            if not primary_val:
                continue

            # Email format validation (req 4.4)
            if data_type == "emails":
                email_val = str(rec.get("email", "")).strip()
                if not email_val or not _EMAIL_PATTERN.fullmatch(email_val):
                    continue
                primary_val = email_val.lower()

            # Deduplication by primary identifier (req 4.4)
            dedup_key = primary_val.lower()
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            cleaned.append(rec)

        return cleaned

    # ------------------------------------------------------------------
    # Delivery summary
    # ------------------------------------------------------------------

    def _build_delivery_summary(
        self,
        data_type: str,
        record_count: int,
        primary_source: str,
        requested_quantity: int,
    ) -> str:
        """Build the delivery_summary string (50-500 chars, req 4.9)."""
        source_display = primary_source[:60] if primary_source else "web search"
        status_note = (
            f"All {requested_quantity} requested records delivered."
            if record_count >= requested_quantity
            else f"Partial delivery: {record_count} of {requested_quantity} requested records collected."
        )
        summary = (
            f"Scraping Lead Gen Agent delivered {record_count} {data_type.replace('_', ' ')} records. "
            f"Primary source: {source_display}. {status_note}"
        )
        # Enforce 50-500 character bounds
        if len(summary) < 50:
            summary = summary + " Data collected via automated web scraping."
        if len(summary) > 500:
            summary = summary[:497] + "..."
        return summary

    # ------------------------------------------------------------------
    # Standalone interactive mode
    # ------------------------------------------------------------------

    def run_interactive(self) -> None:
        """Run the agent interactively from the command line."""
        from rich.panel import Panel

        console.print(Panel(
            "[bold blue]ScrapingLeadGenAgent — Interactive Mode[/bold blue]\n"
            "[dim]Web scraping & lead generation order fulfillment[/dim]",
            border_style="blue",
        ))

        while True:
            try:
                instruction = input(
                    "\nInstruction (or 'exit'): "
                ).strip()
                if instruction.lower() in {"exit", "quit", "q"}:
                    break
                if not instruction:
                    instruction = "Collect 10 business emails from tech startups"

                result = self.run({"instruction": instruction})
                console.print(Panel(
                    f"Status:      {result.get('status', 'unknown')}\n"
                    f"Message:     {result.get('message', '')}\n"
                    f"Records:     {result.get('data', {}).get('record_count', 0)}\n"
                    f"Context:     {result.get('context_for_next', {})}",
                    title="Scraping Lead Gen Result",
                    border_style="blue",
                ))
            except KeyboardInterrupt:
                console.print("\n[dim]ScrapingLeadGenAgent stopped.[/dim]")
                break


if __name__ == "__main__":
    ScrapingLeadGenAgent().run_interactive()
