"""
agents/outreach/research_agent.py
==================================
OUTREACH RESEARCH AGENT
========================
Profiles prospects to enable deep, personalised outreach.

Delegation model (uses shared agents, no duplication):
- Web search / page reading  →  agents/external/web_research_agent.WebResearchAgent
- Competitive / company profiling  →  agents/external/competitive_analysis_agent.CompetitiveAnalysisAgent
- Browser deep-dives (LinkedIn pages, etc.)  →  agents/browser_operator_agent.BrowserOperatorAgent

This agent's unique value:
- Glues the three sources above into a single, structured Prospect Profile.
- Tailors the research angle specifically to outreach (pain points, digital presence,
  recent news hooks, decision-maker identification).
- Exposes run() / get_metadata() for compatibility with the Supreme Orchestrator.

Fallback behaviour:
- If WebResearchAgent is unavailable → uses BrowserOperatorAgent directly.
- If BrowserOperatorAgent is also unavailable → uses rule-based heuristics.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core import make_client
from agents.outreach.context import OutreachContext, ICPMatchResult, VALID_OUTREACH_TYPES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OutreachResearchAgent")

RESEARCH_SYSTEM_PROMPT = """
You are a Research Analyst for an elite AI Outreach Swarm.
You receive raw web research findings, competitive analysis data, and browser snapshots,
then synthesise them into a highly structured Prospect Profile for use by the outreach team.

Your output MUST include all six sections:

1. Prospect Overview
   - Full name, current title, key responsibilities.

2. Company Profile
   - Name, estimated size (employees/revenue tier), industry vertical,
     primary product or service, core customer base.

3. Digital Presence
   - LinkedIn URL, company website, Facebook/Instagram handles (if found).
   - Indicate "NOT FOUND" for any missing.

4. Key Decision Makers
   - Founders, C-suite, department heads visible from public sources.

5. Recent News & Activities
   - Funding rounds, product launches, press mentions, active social posts.
   - Flag each item with its source URL.

6. Potential Pain Points & Value Alignment
   - Based on company stage, industry norms, and recent activities, what
     operational problems are they likely facing?
   - Map each pain point to a specific capability our outreach offers.

Rules:
- State the source URL for every factual claim.
- Flag inferred information with "(INFERRED)".
- Keep the output objective — no marketing language.
- If data is contradictory across sources, note both versions.
"""


class ResearchAgent:
    """
    Outreach Research Agent.
    Delegates web research to WebResearchAgent and CompetitiveAnalysisAgent,
    then synthesises a Prospect Profile specific to outreach needs.
    """

    name = "outreach_research_agent"
    role = "worker"
    description = (
        "Profiles a named prospect (person + company) for personalised outreach. "
        "Gathers LinkedIn data, company news, pain points, and digital presence. "
        "Delegates web search to WebResearchAgent and deep company profiling to "
        "CompetitiveAnalysisAgent. Returns a structured Prospect Profile. "
        "Best for: outreach prep, lead qualification, ICP matching."
    )

    def __init__(self, client=None, verbose: bool = False):
        self.verbose = verbose
        self.client = client or self._init_client()
        self._web_research_agent = self._load_web_research_agent()
        self._competitive_agent = self._load_competitive_agent()
        self._browser_operator = self._load_browser_operator()

    # ── Client init ──────────────────────────────────────────────────────────

    def _init_client(self):
        try:
            return make_client(
                RESEARCH_SYSTEM_PROMPT,
                "OUTREACH-Research",
                api_key=os.getenv("GOOGLE_API_KEY_4") or os.getenv("GOOGLE_API_KEY")
            )
        except Exception as e:
            logger.warning(f"LLM client init failed: {e}. Synthesis will use rule fallback.")
            return None

    # ── Shared agent loaders (graceful failures) ──────────────────────────────

    def _load_web_research_agent(self):
        try:
            from agents.external.web_research_agent import WebResearchAgent
            agent = WebResearchAgent(verbose=self.verbose)
            logger.info("WebResearchAgent loaded successfully.")
            return agent
        except Exception as e:
            logger.warning(f"WebResearchAgent unavailable: {e}")
            return None

    def _load_competitive_agent(self):
        try:
            from agents.external.competitive_analysis_agent import CompetitiveAnalysisAgent
            agent = CompetitiveAnalysisAgent(verbose=self.verbose)
            logger.info("CompetitiveAnalysisAgent loaded successfully.")
            return agent
        except Exception as e:
            logger.warning(f"CompetitiveAnalysisAgent unavailable: {e}")
            return None

    def _load_browser_operator(self):
        try:
            from agents.browser_operator_agent import BrowserOperatorAgent
            agent = BrowserOperatorAgent()
            logger.info("BrowserOperatorAgent loaded successfully.")
            return agent
        except Exception as e:
            logger.warning(f"BrowserOperatorAgent unavailable: {e}")
            return None

    # ── Registry interface ────────────────────────────────────────────────────

    def get_metadata(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "skills": ["prospect_research_skill", "web_search_skill", "competitive_analysis_skill"],
        }

    def run(self, input_data: dict) -> dict:
        """
        Supreme Orchestrator-compatible run() method.

        Args:
            input_data: {
                "task_id": str,
                "instruction": str,          # Free-text: "Research Alice Johnson at InnovateCorp"
                "context": {
                    "prospect_name": str,
                    "prospect_company": str,
                    "target_industry": str,  # optional
                }
            }
        """
        task_id = input_data.get("task_id", "research_task")
        ctx = input_data.get("context", {})
        instruction = input_data.get("instruction", "")

        # Extract structured fields from context or parse from instruction
        name = ctx.get("prospect_name") or self._extract_from_instruction(instruction, "name")
        company = ctx.get("prospect_company") or self._extract_from_instruction(instruction, "company")
        industry = ctx.get("target_industry", "")

        try:
            profile = self.gather_info(name, company, industry)
            return {
                "success": True,
                "agent_name": self.name,
                "task_id": task_id,
                "output": profile,
                "error": None,
                "metadata": {"prospect_name": name, "company": company},
                "context_for_next": {"prospect_profile": profile},
            }
        except Exception as e:
            return {
                "success": False,
                "agent_name": self.name,
                "task_id": task_id,
                "output": None,
                "error": str(e),
                "metadata": {},
                "context_for_next": {},
            }

    # ── Core research pipeline ────────────────────────────────────────────────

    def gather_info(self, target_name: str, target_company: str, target_industry: str = "", context: OutreachContext = None) -> str:
        """
        Main pipeline:
        1. Web research via WebResearchAgent (or BrowserOperator fallback)
        2. Company competitive profile via CompetitiveAnalysisAgent
        3. Synthesis via LLM (or rule fallback)
        4. Type-aware research focus based on OutreachContext
        
        Args:
            target_name: Prospect's name
            target_company: Prospect's company
            target_industry: Optional industry hint
            context: Optional OutreachContext for type-aware research
        """
        logger.info(f"Starting research: {target_name} @ {target_company}")
        findings = {}
        
        # Store context for type-aware research
        self._current_context = context

        # ── Layer 1: Web Research ─────────────────────────────────────────────
        if self._web_research_agent:
            findings["web"] = self._run_web_research(target_name, target_company, target_industry)
        elif self._browser_operator:
            findings["web"] = self._run_browser_search(target_name, target_company)
        else:
            logger.warning("No web research agent available. Skipping web layer.")
            findings["web"] = {}

        # ── Layer 2: Competitive / Company Profile ────────────────────────────
        if self._competitive_agent:
            findings["competitive"] = self._run_competitive_analysis(target_company, target_industry)
        else:
            logger.warning("CompetitiveAnalysisAgent unavailable. Skipping competitive layer.")
            findings["competitive"] = {}

        # ── Layer 3: LinkedIn / Direct Profile Lookup ─────────────────────────
        if self._browser_operator:
            findings["linkedin"] = self._run_linkedin_lookup(target_name, target_company)
        else:
            findings["linkedin"] = {}

        return self._synthesize_profile(target_name, target_company, findings)

    def _run_web_research(self, name: str, company: str, industry: str) -> dict:
        """Delegates to WebResearchAgent for general web research."""
        logger.info("Delegating to WebResearchAgent...")
        queries = [
            f"{name} {company} CEO founder executive profile",
            f"{company} {industry} recent news funding product launch",
            f"{company} site:linkedin.com",
        ]
        combined = {}
        for query in queries:
            try:
                result = self._web_research_agent.research(query, depth="shallow", max_searches=2)
                combined[query] = {
                    "summary": result.get("summary", ""),
                    "key_findings": result.get("key_findings", []),
                    "sources": result.get("sources", []),
                }
            except Exception as e:
                logger.error(f"WebResearchAgent query failed for '{query}': {e}")
                combined[query] = {"error": str(e)}
        return combined

    def _run_competitive_analysis(self, company: str, industry: str) -> dict:
        """Delegates to CompetitiveAnalysisAgent for company landscape data."""
        logger.info("Delegating to CompetitiveAnalysisAgent...")
        try:
            result = self._competitive_agent.analyze(
                company=company,
                industry=industry or "General Technology"
            )
            return result
        except Exception as e:
            logger.error(f"CompetitiveAnalysisAgent failed: {e}")
            return {"error": str(e)}

    def _run_browser_search(self, name: str, company: str) -> dict:
        """Fallback: uses BrowserOperatorAgent when WebResearchAgent is unavailable."""
        logger.info("Falling back to BrowserOperatorAgent for web search...")
        queries = [
            f"{name} {company} LinkedIn profile",
            f"{company} official website services",
        ]
        results = {}
        for query in queries:
            try:
                result = self._browser_operator.run_task(query)
                summary = result.get("summary", {})
                results[query] = {
                    "top_finding": summary.get("top_finding"),
                    "visited_urls": summary.get("visited_urls", []),
                }
            except Exception as e:
                logger.error(f"BrowserOperator query failed: '{query}': {e}")
                results[query] = {"error": str(e)}
        return results

    def _run_linkedin_lookup(self, name: str, company: str) -> dict:
        """Uses BrowserOperatorAgent to fetch LinkedIn profile data."""
        logger.info("Running LinkedIn profile lookup via BrowserOperatorAgent...")
        try:
            result = self._browser_operator.run_task(
                f"site:linkedin.com/in {name} {company}"
            )
            return result.get("summary", {})
        except Exception as e:
            logger.warning(f"LinkedIn lookup failed: {e}")
            return {}

    def _synthesize_profile(self, name: str, company: str, findings: Dict[str, Any]) -> str:
        """Uses LLM to synthesise all findings into a structured Prospect Profile."""
        prompt = (
            f"Synthesise a Prospect Profile for: {name} at {company}\n\n"
            f"Research Findings:\n{json.dumps(findings, indent=2, default=str)}\n\n"
            "Output the full six-section Prospect Profile as specified in the system prompt. "
            "Include source URLs for every factual claim."
        )
        if self.client:
            try:
                if hasattr(self.client, "generate_content"):
                    return self.client.generate_content(prompt).text
                elif hasattr(self.client, "invoke"):
                    resp = self.client.invoke(prompt)
                    return getattr(resp, "content", str(resp))
                elif hasattr(self.client, "ask"):
                    return self.client.ask(prompt)
            except Exception as e:
                logger.error(f"LLM synthesis failed: {e}. Using rule fallback.")
        return self._fallback_profile(name, company, findings)

    def _fallback_profile(self, name: str, company: str, findings: Dict[str, Any]) -> str:
        """Rule-based profile generator when LLM is unavailable."""
        logger.info("Using rule-based fallback profile generator.")
        web = findings.get("web", {})
        comp = findings.get("competitive", {})
        linkedin = findings.get("linkedin", {})

        # Extract any URLs we found
        sources = []
        for query_data in web.values():
            if isinstance(query_data, dict):
                sources.extend(query_data.get("sources", []))

        executive_summary = comp.get("executive_summary", "(Not available)")
        market_gaps = comp.get("market_gaps", [])
        linkedin_url = linkedin.get("top_finding", {})
        if isinstance(linkedin_url, dict):
            linkedin_url = linkedin_url.get("source_url", "Not verified")

        return f"""
# PROSPECT PROFILE — {name} at {company}

### 1. Prospect Overview
- **Name**: {name}
- **Title**: Executive / Decision Maker (INFERRED — verify via LinkedIn)
- **Responsibilities**: Strategic direction, operations oversight (INFERRED)

### 2. Company Profile
- **Company**: {company}
- **Industry**: General Technology / Services (INFERRED)
- **Market Context**: {executive_summary}

### 3. Digital Presence
- **LinkedIn**: {linkedin_url}
- **Website**: (Check competitive analysis data)
- **Social**: (Requires manual verification)

### 4. Key Decision Makers
- {name} — primary contact identified
- Additional executives: (INFERRED — verify via LinkedIn)

### 5. Recent News & Activities
{chr(10).join(f"- {src.get('title', '')} — {src.get('url', '')}" for src in sources[:5]) or "- No recent news found."}

### 6. Pain Points & Value Alignment
{chr(10).join(f"- {gap}" for gap in market_gaps[:3]) if market_gaps else "- Manual operations overhead (INFERRED)"}
- Multi-platform communication management gaps (INFERRED)
- Outreach automation and scaling challenges (INFERRED)

---
*Compiled via rule-based fallback. LLM synthesis unavailable.*
"""

    def _extract_from_instruction(self, instruction: str, field: str) -> str:
        """Best-effort extraction of name/company from free-text instruction."""
        # Very simple heuristic — the LLM will handle real parsing
        words = instruction.split()
        if field == "name" and len(words) >= 2:
            return f"{words[0]} {words[1]}"
        if field == "company" and "at " in instruction:
            return instruction.split("at ")[-1].strip().split()[0]
        return "Unknown"

    # ── ICP Scoring (NEW) ───────────────────────────────────────────────────────

    def score_icp_match(self, profile: str, icp: Dict[str, Any]) -> ICPMatchResult:
        """
        Score a prospect profile against the Ideal Customer Profile.
        
        Args:
            profile: The prospect profile text (from gather_info)
            icp: ICP constraints dictionary with:
                - industries: List of target industries
                - seniority_levels: List of target seniority levels
                - company_size_range: Target company size (e.g., "1-50", "1000+")
                - geo: List of target geographies
                - keywords: List of keywords that indicate good fit
                - exclusions: List of exclusion keywords
                - min_icp_score: Minimum score threshold (default 0.3)
        
        Returns:
            ICPMatchResult with score, matched/failed criteria, and recommendation
        """
        profile_lower = profile.lower()
        matched_criteria = []
        failed_criteria = []
        total_checks = 0
        passed_checks = 0
        
        # Check industries
        industries = icp.get("industries", [])
        if industries:
            total_checks += 1
            industry_found = any(ind.lower() in profile_lower for ind in industries)
            if industry_found:
                matched_criteria.append(f"Industry match: found target industry")
                passed_checks += 1
            else:
                failed_criteria.append("Industry not in target list")
        
        # Check seniority levels
        seniority = icp.get("seniority_levels", [])
        if seniority:
            total_checks += 1
            seniority_keywords = {
                "C-Level": ["ceo", "cto", "cfo", "coo", "chief", "founder", "president"],
                "VP/Director": ["vp", "vice president", "director", "head of"],
                "Manager": ["manager", "lead", "senior"],
            }
            seniority_found = False
            for level in seniority:
                keywords = seniority_keywords.get(level, [level.lower()])
                if any(kw in profile_lower for kw in keywords):
                    seniority_found = True
                    break
            if seniority_found:
                matched_criteria.append(f"Seniority match: target level found")
                passed_checks += 1
            else:
                failed_criteria.append("Seniority not in target list")
        
        # Check company size
        size_range = icp.get("company_size_range", "")
        if size_range:
            total_checks += 1
            # Simple heuristic: look for employee counts or size indicators
            size_found = False
            size_patterns = {
                "1-50": ["startup", "small team", "1-50", "under 50", "seed", "early stage"],
                "50-200": ["50-200", "mid-size", "growing team"],
                "200-1000": ["200-1000", "scale-up", "mid-market"],
                "1000+": ["enterprise", "1000+", "fortune", "large company", "global"],
            }
            patterns = size_patterns.get(size_range, [])
            if any(p in profile_lower for p in patterns):
                size_found = True
            if size_found:
                matched_criteria.append(f"Company size match: {size_range}")
                passed_checks += 1
            else:
                failed_criteria.append(f"Company size not in target range ({size_range})")
        
        # Check geography
        geo = icp.get("geo", [])
        if geo:
            total_checks += 1
            geo_found = any(g.lower() in profile_lower for g in geo)
            if geo_found:
                matched_criteria.append(f"Geography match")
                passed_checks += 1
            else:
                failed_criteria.append("Geography not in target list")
        
        # Check keywords (positive signals)
        keywords = icp.get("keywords", [])
        if keywords:
            total_checks += 1
            keywords_found = [kw for kw in keywords if kw.lower() in profile_lower]
            if keywords_found:
                matched_criteria.append(f"Keyword matches: {', '.join(keywords_found[:3])}")
                passed_checks += 1
            else:
                failed_criteria.append("No target keywords found")
        
        # Check exclusions (negative signals)
        exclusions = icp.get("exclusions", [])
        if exclusions:
            exclusions_found = [ex for ex in exclusions if ex.lower() in profile_lower]
            if exclusions_found:
                failed_criteria.append(f"Exclusion triggers: {', '.join(exclusions_found[:3])}")
                # Strong penalty for exclusions
                total_checks += len(exclusions_found)
        
        # Calculate score
        if total_checks == 0:
            score = 0.5  # Neutral score if no ICP criteria defined
        else:
            score = passed_checks / max(total_checks, 1)
        
        # Cap at 1.0
        score = min(score, 1.0)
        
        # Determine recommendation
        min_score = icp.get("min_icp_score", 0.3)
        if score >= min_score:
            recommendation = "APPROVE"
        elif score >= min_score * 0.5:
            recommendation = "DEPRIORITIZE"
        else:
            recommendation = "REJECT"
        
        return ICPMatchResult(
            score=score,
            matched_criteria=matched_criteria,
            failed_criteria=failed_criteria,
            recommendation=recommendation,
            confidence=min(score + 0.1, 1.0),  # Slight confidence boost
        )

    def _get_type_aware_queries(self, name: str, company: str, context: OutreachContext) -> List[str]:
        """
        Generate research queries tailored to the outreach type.
        
        Args:
            name: Prospect name
            company: Prospect company
            context: OutreachContext with outreach_type
        
        Returns:
            List of type-specific search queries
        """
        base_queries = [f"{name} {company} profile", f"{company} recent news"]
        
        type_specific = {
            "INVESTOR": [
                f"{name} investment portfolio fund thesis",
                f"{company} funding rounds investors portfolio",
                f"{name} investments made sectors",
            ],
            "RECRUITMENT": [
                f"{name} career trajectory roles history",
                f"{company} careers open roles hiring",
                f"{name} LinkedIn work experience",
            ],
            "PARTNERSHIP": [
                f"{company} tech stack integrations partners",
                f"{company} strategic partnerships alliances",
                f"{name} partnerships collaborations",
            ],
            "EVENT_PROMO": [
                f"{name} speaking engagements conferences",
                f"{company} events webinars hosted",
                f"{name} event attendance industry conferences",
            ],
            "PR_MEDIA": [
                f"{name} interviews articles quotes",
                f"{company} press releases media coverage",
                f"{name} thought leadership publications",
            ],
            "CUSTOMER_SUCCESS": [
                f"{company} customer success retention",
                f"{name} account management role",
                f"{company} product usage case studies",
            ],
            "LEAD_GEN": [
                f"{name} decision maker executive",
                f"{company} pain points challenges needs",
                f"{name} company growth initiatives",
            ],
        }
        
        specific = type_specific.get(context.outreach_type, [])
        return base_queries + specific


# ── CLI mock simulation ───────────────────────────────────────────────────────
def run_interactive_simulation():
    print("=" * 60)
    print("Outreach Research Agent — Integration Simulation")
    print("=" * 60)
    print("Agents loaded: WebResearchAgent, CompetitiveAnalysisAgent, BrowserOperatorAgent")
    print()

    agent = ResearchAgent(verbose=True)
    print(f"\nRegistry metadata: {json.dumps(agent.get_metadata(), indent=2)}")

    result = agent.run({
        "task_id": "test_001",
        "instruction": "Research Alice Johnson at InnovateCorp",
        "context": {
            "prospect_name": "Alice Johnson",
            "prospect_company": "InnovateCorp",
            "target_industry": "Enterprise Software",
        }
    })
    print(f"\nSuccess: {result['success']}")
    print(f"Output preview:\n{str(result.get('output', ''))[:500]}")


if __name__ == "__main__":
    run_interactive_simulation()
