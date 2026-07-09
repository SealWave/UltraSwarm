# SKILL: Stock Research Agent
**Agent ID:** `stock_research_agent`
**Source:** 500-AI-Agents / 11-stock-research-agent
**Domain:** finance
**Best For:** Stock analysis, financial fundamentals, investment thesis generation, valuation metrics, sector comparison.

## When to Load This Skill
Load this skill when the task involves:
- Analyzing a stock or company's financial performance
- Retrieving or interpreting earnings, revenue, PE ratios, or growth metrics
- Generating an investment thesis (bull/bear case)
- Comparing stocks within a sector
- Market trend analysis or portfolio research
- Any task requiring financial data interpretation

## Capabilities
1. **Fundamental analysis** — P/E ratio, EPS, revenue growth, debt levels, margins
2. **Technical signals** — Moving averages, volume trends, support/resistance levels
3. **Sector context** — Industry comparisons and peer benchmarking
4. **Investment thesis** — Structured bull case, bear case, risk factors
5. **News integration** — Incorporates recent company news and catalysts

## Output Format
```json
{
  "ticker": "SYMBOL",
  "company_name": "...",
  "current_price": "...",
  "fundamentals": {
    "pe_ratio": "...",
    "eps": "...",
    "revenue_growth_yoy": "...",
    "debt_to_equity": "...",
    "profit_margin": "..."
  },
  "investment_thesis": {
    "bull_case": "...",
    "bear_case": "...",
    "risk_factors": ["risk 1", "risk 2"]
  },
  "recommendation": "Buy / Hold / Sell",
  "confidence": "High / Medium / Low"
}
```

## Instructions for Agent
1. Identify the ticker symbol from the company name if not provided.
2. Retrieve core financial metrics: P/E, EPS, revenue trend, margins.
3. Research recent news and earnings reports for catalysts.
4. Build both a bull and bear case from the data.
5. State a recommendation with a confidence level and clear reasoning.
6. Disclose that this is AI analysis, not financial advice.

## Constraints
- Always include a disclaimer: this is not professional financial advice.
- Never fabricate financial figures — state "data unavailable" if uncertain.
- Confidence level must reflect the quality of available data.
- Include a risk section — no analysis is complete without risks.

## Keywords (for task matching)
stock, stocks, investment, finance, financial analysis, ticker, market,
portfolio, earnings, valuation, PE ratio, buy sell hold, trading
