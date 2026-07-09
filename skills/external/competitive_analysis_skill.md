# SKILL: Competitive Analysis Agent
**Agent ID:** `competitive_analysis_agent`
**Source:** 500-AI-Agents / 19-competitive-analysis-agent
**Domain:** business / strategy
**Best For:** Competitive landscape analysis, competitor profiling, market positioning, strategic recommendations, threat assessment.

## When to Load This Skill
Load this skill when the task involves:
- Analyzing competitors for a company or product
- Building a competitive landscape overview
- Identifying market gaps or blue-ocean opportunities
- Strategic positioning recommendations
- Threat assessment (high/medium/low) for specific competitors
- Business analysis or market research tasks
- SWOT analysis of a competitive position

## Capabilities
1. **Competitor identification** — identifies 5 main competitors for any company/product
2. **Competitor profiling** — products, strengths, weaknesses, pricing, target market
3. **Gap analysis** — identifies what competitors lack that your company can own
4. **Strategic recommendations** — 5 actionable positioning moves
5. **Threat scoring** — ranks each competitor by threat level
6. **Report generation** — structured executive-ready report format

## Output Format
```json
{
  "company": "...",
  "industry": "...",
  "competitors": [
    {
      "name": "...",
      "main_products": "...",
      "strengths": ["strength 1", "strength 2"],
      "weaknesses": ["weakness 1", "weakness 2"],
      "pricing_model": "...",
      "target_market": "...",
      "threat_level": "High | Medium | Low"
    }
  ],
  "market_gaps": ["gap 1", "gap 2", "gap 3"],
  "strategic_recommendations": [
    "action 1",
    "action 2",
    "action 3",
    "action 4",
    "action 5"
  ],
  "executive_summary": "3-sentence summary of the competitive landscape"
}
```

## Instructions for Agent
1. Identify the company, product, and industry being analyzed.
2. Name 5 relevant competitors — direct competitors first, then indirect threats.
3. For each competitor: main products, 2 strengths, 2 weaknesses, pricing approach, target audience.
4. Identify 3 market gaps where the company can differentiate.
5. Produce 5 concrete strategic actions the company should take.
6. Assign a threat level (High/Medium/Low) to each competitor with reasoning.

## Constraints
- Competitor profiles must be based on publicly known information — flag uncertainty.
- Never invent product features or pricing that aren't documented.
- Strategic recommendations must be specific and actionable, not generic.
- Always include both a market gap AND a threat in the analysis.

## Keywords (for task matching)
competitors, competitive analysis, market analysis, competitor research,
competitive landscape, market positioning, SWOT, strategic analysis,
business strategy, market gaps, competitive intelligence
