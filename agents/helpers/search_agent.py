from core.base_agent import BaseAgent
from core.result_schema import AgentResult
from tools.browser import google_search, fetch_page
from tools.summarizer import chunk_and_summarize


class SearchAgent(BaseAgent):

    name = "search_agent"
    role = "helper"
    description = (
        "Web research agent. Given a search query or research topic, performs "
        "Google searches, reads top result pages, and returns a structured "
        "summary of findings. Best for: gathering external information, "
        "fact-checking, competitive research, current events."
    )
    default_skills = [
        "google_search_skill",   # How to construct and execute searches
        "web_summarize_skill",   # How to summarize web page content
    ]
    base_system_prompt = """
You are the Search Agent — an expert web researcher.

Your job is to:
1. Receive a research topic or question.
2. Formulate 1-3 targeted search queries.
3. Execute those searches using the tools available to you.
4. Read the most relevant pages.
5. Synthesize a clear, factual summary of your findings.

OUTPUT FORMAT: Always return a JSON object with this structure:
{
  "summary": "Prose summary of findings (200-400 words)",
  "key_facts": ["fact 1", "fact 2", "..."],
  "sources": [{"title": "...", "url": "..."}],
  "search_queries_used": ["query 1", "query 2"]
}

RULES:
- Cite sources for every factual claim.
- If search results are conflicting, note the conflict in your summary.
- Never fabricate URLs or facts.
- If you cannot find relevant information, say so clearly in the summary.
"""

    def run(self, input_data: dict) -> dict:
        """
        Perform a web search and return summarized findings.

        Args:
            input_data: {
                "task_id": str,
                "instruction": str,      # The research question or topic
                "context": dict,         # May contain previous search results
                "max_searches": int,     # Default: 3
                "depth": str,            # "shallow" (snippets only) | "deep" (read pages)
            }

        Returns:
            AgentResult with output = research summary dict.
        """
        instruction = input_data.get("instruction", "")
        task_id = input_data.get("task_id", "search_task")
        max_searches = input_data.get("max_searches", 3)
        depth = input_data.get("depth", "deep")

        # Step 1: Generate search queries
        query_prompt = (
            f"Research task: {instruction}\n\n"
            f"Generate {max_searches} targeted Google search queries for this task. "
            f"Return ONLY a JSON array of query strings."
        )
        try:
            queries = self.chat_json(query_prompt, reset_history=True)
            if not isinstance(queries, list):
                queries = [instruction]  # Fallback to raw instruction
        except ValueError:
            queries = [instruction]

        # Step 2: Execute searches and collect raw content
        raw_content = []
        sources = []
        for query in queries[:max_searches]:
            search_results = google_search(query, max_results=5)
            for result in search_results:
                sources.append({"title": result["title"], "url": result["url"]})
                if depth == "deep":
                    page_text = fetch_page(result["url"])
                    if page_text:
                        raw_content.append(f"SOURCE: {result['url']}\n{page_text[:3000]}")
                else:
                    raw_content.append(result.get("snippet", ""))

        # Step 3: Summarize collected content
        combined = "\n\n---\n\n".join(raw_content)
        if len(combined) > 8000:
            combined = chunk_and_summarize(combined, target_length=6000)

        synthesis_prompt = (
            f"Research task: {instruction}\n\n"
            f"Here is the raw content from web searches:\n\n{combined}\n\n"
            f"Synthesize this into a structured JSON response with keys: "
            f"summary, key_facts, sources, search_queries_used."
        )

        try:
            result_data = self.chat_json(synthesis_prompt, reset_history=False)
            result_data["sources"] = sources  # Ensure sources are populated
            result_data["search_queries_used"] = queries

            return AgentResult(
                success=True,
                agent_name=self.name,
                task_id=task_id,
                output=result_data,
                context_for_next={"search_results": result_data}
            ).to_dict()
        except ValueError as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                task_id=task_id,
                output=None,
                error=str(e)
            ).to_dict()
