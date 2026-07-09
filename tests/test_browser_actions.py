import unittest
from unittest.mock import Mock, patch

from tools.browser import AgentBrowser
from tools.browser_actions import BrowserActionRunner, BrowserPlannerLoop, extract_product_data_from_snapshot
from tools.swarm_memory import SwarmMemory


class FakeBrowser:
    def __init__(self):
        self.calls = []
        self.snapshot_text = """
@e1 [input type="search"] placeholder="Search products"
@e2 [button] "Search"
@e3 [h2] "Compact Climbing Harness"
@e4 [text] "$18.50"
@e5 [text] "4.7 stars"
@e6 [text] "1,284 orders"
"""

    def fetch_page(self, url):
        self.calls.append(("open", url))
        return {"url": url, "title": "Supplier", "text": self.snapshot_text, "status": "ok"}

    def snapshot(self):
        self.calls.append(("snapshot",))
        return {"text": self.snapshot_text, "status": "ok"}

    def type_text(self, ref, text):
        self.calls.append(("fill", ref, text))
        return True

    def click(self, ref):
        self.calls.append(("click", ref))
        return True

    def wait(self, ms):
        self.calls.append(("wait", ms))
        return True

    def scroll(self, direction="down", amount=500):
        self.calls.append(("scroll", direction, amount))
        return True

    def press(self, key):
        self.calls.append(("press", key))
        return True


class ErrorClient:
    def ask_json(self, prompt, schema_hint=""):
        return {"raw_response": "[BROWSE ERROR]: 429 quota exceeded", "parse_error": True}


class RateLimitClient:
    def ask_json(self, prompt, schema_hint=""):
        return {
            "raw_response": "[BROWSE ERROR]: 429 quota exceeded. Please retry in 58.5s.",
            "parse_error": True,
            "rate_limited": True,
            "retry_after_seconds": 59,
        }


class BrowserActionRunnerTests(unittest.TestCase):
    def test_runner_finds_refs_from_snapshot_and_fills_by_hint(self):
        memory = SwarmMemory({"goal": "source climbing gear"})
        browser = FakeBrowser()
        runner = BrowserActionRunner(browser=browser)

        open_result = runner.run_step({"action": "open", "url": "https://supplier.test"}, memory)
        fill_result = runner.run_step({"action": "fill", "hint": "Search products", "text": "climbing gear"}, memory)

        self.assertTrue(open_result["success"])
        self.assertTrue(fill_result["success"])
        self.assertEqual(fill_result["ref"], "@e1")
        self.assertIn(("fill", "@e1", "climbing gear"), browser.calls)
        self.assertEqual(memory.get("browser_state.current_url"), "https://supplier.test")

    def test_runner_rejects_unapproved_actions(self):
        runner = BrowserActionRunner(browser=FakeBrowser())

        result = runner.run_step({"action": "eval", "script": "document.cookie"})

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "action_not_allowed")

    def test_runner_can_fill_from_swarm_memory_path(self):
        memory = SwarmMemory({"admin": {"password": "secret-value"}})
        browser = FakeBrowser()
        runner = BrowserActionRunner(browser=browser)
        runner.run_step({"action": "open", "url": "https://admin.test"}, memory)

        result = runner.run_step(
            {"action": "fill", "hint": "Search products", "text_from": "admin.password"},
            memory,
        )

        self.assertTrue(result["success"])
        self.assertIn(("fill", "@e1", "secret-value"), browser.calls)

    def test_extract_product_data_finds_commercial_signals(self):
        data = extract_product_data_from_snapshot(FakeBrowser().snapshot_text)

        self.assertEqual(data["product_name"], "Compact Climbing Harness")
        self.assertEqual(data["price"], "18.50")
        self.assertEqual(data["rating"], "4.7")
        self.assertEqual(data["order_count"], 1284)
        self.assertIn("Compact Climbing Harness", data["description"])

    def test_open_action_normalizes_url_without_scheme(self):
        memory = SwarmMemory()
        browser = FakeBrowser()
        runner = BrowserActionRunner(browser=browser)

        result = runner.run_step({"action": "open", "url": "www.wikipedia.org"}, memory)

        self.assertTrue(result["success"])
        self.assertEqual(result["url"], "https://www.wikipedia.org")
        self.assertIn(("open", "https://www.wikipedia.org"), browser.calls)

    def test_planner_stops_when_backend_returns_parse_error(self):
        runner = BrowserActionRunner(browser=FakeBrowser())
        loop = BrowserPlannerLoop(ErrorClient(), runner, max_steps=5)

        result = loop.run("open a page", SwarmMemory())

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "planner_error")
        self.assertEqual(len(result["steps"]), 1)

    def test_planner_stops_with_retry_after_when_rate_limited(self):
        runner = BrowserActionRunner(browser=FakeBrowser())
        loop = BrowserPlannerLoop(RateLimitClient(), runner, max_steps=5)

        result = loop.run("open a page", SwarmMemory())

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "rate_limited")
        self.assertEqual(result["retry_after_seconds"], 59)
        self.assertEqual(len(result["steps"]), 1)

    @patch("tools.browser.requests.get")
    def test_duckduckgo_search_parses_real_result_links(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.text = """
        <html>
          <a class="result__a" href="https://example.com/laptop-1">Laptop One</a>
          <a class="result__snippet">32 GB RAM under $400</a>
        </html>
        """
        mock_get.return_value = mock_response

        results = AgentBrowser.search("laptop 32 gb ram under 400")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Laptop One")
        self.assertEqual(results[0]["url"], "https://example.com/laptop-1")


if __name__ == "__main__":
    unittest.main()
