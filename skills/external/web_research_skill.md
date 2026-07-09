# SKILL: Web Research Agent
**Agent ID:** `web_research_agent`
**Source:** 500-AI-Agents / 01-web-research-agent
**Domain:** research
**Best For:** Searching the web, synthesizing multi-source research reports, fact-finding, current-events queries, background investigation on any topic.

## When to Load This Skill
Load this skill when the task involves:
- Gathering information from the internet about any topic
- Synthesizing multiple sources into a structured research report
- Answering questions that require current or external knowledge
- Background research before writing, analysis, or strategy work
- Verifying claims or finding supporting evidence

## Capabilities
1. **Multi-query web search** — formulates 1-5 targeted search queries per topic
2. **Source synthesis** — reads top results and extracts key facts, not just snippets
3. **Structured reporting** — returns Summary, Key Findings (bullets), and cited Sources
4. **Topic flexibility** — works on any subject: technology, markets, people, products, events

## Output Format
```json
{
  "summary": "200-400 word prose synthesis of findings",
  "key_findings": ["finding 1", "finding 2", "..."],
  "sources": [{"title": "...", "url": "..."}],
  "search_queries_used": ["query 1", "query 2"]
}
```

## Instructions for Agent
1. Formulate 2-4 diverse search queries covering the topic from different angles.
2. Search and retrieve top results for each query.
3. Cross-reference facts across sources — note conflicts if present.
4. Synthesize into a structured report; every factual claim must cite a source.
5. Lead with the most important finding in the summary.
6. Never fabricate URLs, statistics, or quotes.

## Constraints
- Max 10 search queries per task.
- Always cite source URL for every key finding.
- If no credible sources found, state clearly — do not hallucinate.
- Keep summaries under 500 words unless explicitly asked for more depth.

## Keywords (for task matching)
research, web search, find information, look up, investigate, gather data,
fact-check, current events, background research, sources, synthesize
