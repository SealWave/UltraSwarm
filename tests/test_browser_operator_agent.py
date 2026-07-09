import unittest

from agents.browser_operator_agent import BrowserOperatorAgent
from tools.browser_actions import BrowserActionRunner
from tools.swarm_memory import SwarmMemory


class FakeClient:
    def __init__(self):
        self.steps = iter([
            {"action": "open", "url": "https://example.com"},
            {"action": "snapshot"},
            {"action": "finish"},
        ])

    def ask_json(self, prompt, schema_hint=""):
        return next(self.steps)


class FakeBrowser:
    def fetch_page(self, url):
        return {"url": url, "title": "Example", "text": "@e1 [button] \"Done\"", "status": "ok"}

    def snapshot(self):
        return {"url": "https://example.com", "title": "Example", "text": "@e1 [button] \"Done\"", "status": "ok"}

    def type_text(self, ref, text):
        return True

    def click(self, ref):
        return True

    def wait(self, ms):
        return True

    def scroll(self, direction="down", amount=500):
        return True

    def press(self, key):
        return True


class SearchBrowser(FakeBrowser):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.current_page = None
        self.pages = {
            "https://store.test/laptop-1": {
                "url": "https://store.test/laptop-1",
                "title": "Laptop 1",
                "text": '@e1 [h2] "Laptop 1" @e2 [text] "$399" @e3 [text] "32 GB RAM"',
                "status": "ok",
            },
            "https://store.test/laptop-2": {
                "url": "https://store.test/laptop-2",
                "title": "Laptop 2",
                "text": '@e1 [h2] "Laptop 2" @e2 [text] "$379" @e3 [text] "32 GB RAM"',
                "status": "ok",
            },
        }

    def fetch_page(self, url):
        self.calls.append(("open", url))
        self.current_page = self.pages[url]
        return self.current_page

    def snapshot(self):
        self.calls.append(("snapshot",))
        return self.current_page or self.pages["https://store.test/laptop-1"]


class RateLimitClient:
    def ask_json(self, prompt, schema_hint=""):
        return {
            "raw_response": "[BROWSE ERROR]: 429 quota exceeded. Please retry in 58s.",
            "parse_error": True,
            "rate_limited": True,
            "retry_after_seconds": 58,
        }


class BrowserOperatorAgentTests(unittest.TestCase):
    def test_agent_runs_user_prompt_through_browser_loop(self):
        agent = BrowserOperatorAgent(client=FakeClient(), browser=FakeBrowser(), max_steps=5, save_outputs=False)

        result = agent.run_task("Open example.com and inspect the page")

        self.assertTrue(result["success"])
        self.assertEqual(result["swarm_memory"]["user_prompt"], "Open example.com and inspect the page")
        self.assertEqual(result["swarm_memory"]["browser_state"]["current_url"], "https://example.com")
        self.assertEqual(result["steps"][-1]["step"]["action"], "finish")
        self.assertEqual(result["summary"]["status"], "completed")

    def test_agent_summarizes_rate_limit_without_raw_trace(self):
        agent = BrowserOperatorAgent(client=RateLimitClient(), browser=FakeBrowser(), max_steps=5, save_outputs=False)

        result = agent.run_task("Search the web")

        self.assertFalse(result["success"])
        self.assertEqual(result["summary"]["status"], "rate_limited")
        self.assertEqual(result["summary"]["retry_after_seconds"], 58)

    def test_agent_cleans_empty_values_from_saved_output(self):
        agent = BrowserOperatorAgent(client=FakeClient(), browser=FakeBrowser(), max_steps=5, save_outputs=False)

        raw = {
            "success": True,
            "steps": [
                {
                    "step": {"action": "find", "url": "", "ref": "", "text": "", "hint": "done"},
                    "result": {"success": False, "error": "ref_not_found", "hint": ""},
                }
            ],
            "memory": {
                "browser_state": {
                    "current_url": "",
                    "last_snapshot": "",
                    "completed_steps": [
                        {
                            "step": {"action": "find", "url": "", "ref": "", "text": "", "hint": "done"},
                            "result": {"success": False, "error": "ref_not_found", "hint": ""},
                        }
                    ],
                    "errors": [{"success": False, "error": "ref_not_found", "hint": ""}],
                },
                "product_candidates": [
                    {
                        "product_name": "",
                        "price": "",
                        "rating": "",
                        "order_count": 0,
                        "review_count": 0,
                        "description": "",
                        "raw_snapshot_excerpt": "",
                        "source_url": "",
                        "source_score": 1.0,
                    }
                ],
            },
        }

        cleaned_steps = [agent._clean_step_record(step) for step in raw["steps"]]
        cleaned_memory = agent._clean_memory(raw["memory"])

        self.assertEqual(cleaned_steps[0]["step"], {"action": "find", "hint": "done"})
        self.assertEqual(cleaned_memory["browser_state"]["completed_steps"][0]["step"], {"action": "find", "hint": "done"})
        self.assertNotIn("last_snapshot", cleaned_memory["browser_state"])
        self.assertNotIn("product_candidates", cleaned_memory)

    def test_agent_builds_search_query_for_product_requests(self):
        agent = BrowserOperatorAgent(client=FakeClient(), browser=FakeBrowser(), max_steps=5, save_outputs=False)

        query = agent._build_search_query("find me a laptop that has 32 gb ram under 400 dollars")

        self.assertTrue(query)
        self.assertIn("laptop", query)

    def test_agent_search_flow_extracts_products_without_planner(self):
        agent = BrowserOperatorAgent(client=FakeClient(), browser=SearchBrowser(), max_steps=5, save_outputs=False)
        memory = SwarmMemory({"agent": "BROWSE", "user_prompt": "find me a laptop that has 32 gb ram give me 3 of them they should cost less then 400 dollars"})
        runner = BrowserActionRunner(agent.browser)
        search_results = [
            {"title": "Laptop 1", "url": "https://store.test/laptop-1", "snippet": "32 GB RAM"},
            {"title": "Laptop 2", "url": "https://store.test/laptop-2", "snippet": "32 GB RAM"},
        ]

        result = agent._run_search_task(
            "find me a laptop that has 32 gb ram give me 3 of them they should cost less then 400 dollars",
            "find me a laptop that has 32 gb ram give me 3 of them they should cost less then 400 dollars",
            search_results,
            memory,
            runner,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["summary"]["findings_count"], 2)
        self.assertEqual(result["summary"]["top_finding"]["product_name"], "Laptop 1")
        self.assertEqual(result["summary"]["visited_urls"], ["https://store.test/laptop-1", "https://store.test/laptop-2"])

    def test_agent_extracts_generic_constraints_from_prompt(self):
        agent = BrowserOperatorAgent(client=FakeClient(), browser=FakeBrowser(), max_steps=5, save_outputs=False)

        constraints = agent._extract_constraints("find me a laptop with touchscreen and 16 gb ram under 500 dollars")

        self.assertEqual(constraints["price_max"], 500.0)
        self.assertIn("laptop", constraints["keywords"])
        self.assertIn("touchscreen", constraints["keywords"])
        self.assertIn("ram", constraints["keywords"])

    def test_agent_matches_generic_specs_against_page_text(self):
        agent = BrowserOperatorAgent(client=FakeClient(), browser=FakeBrowser(), max_steps=5, save_outputs=False)
        constraints = agent._extract_constraints("find me a laptop with touchscreen and 16 gb ram under 500 dollars")
        product = {"product_name": "Budget Laptop", "price": "479", "description": "16 GB RAM touchscreen laptop"}
        search_result = {"title": "Budget Laptop", "snippet": "touchscreen 16 GB RAM"}

        self.assertTrue(agent._candidate_matches(constraints, product, search_result))
        self.assertIn("touchscreen", agent._matched_constraints(constraints, product, search_result))


if __name__ == "__main__":
    unittest.main()
