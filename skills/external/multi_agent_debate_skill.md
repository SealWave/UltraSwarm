# SKILL: Multi-Agent Debate System
**Agent ID:** `multi_agent_debate_agent`
**Source:** 500-AI-Agents / 20-multi-agent-debate
**Domain:** research / reasoning
**Best For:** Structured argumentation on any topic — two-sided debate with scoring, pros/cons analysis, devil's advocate reasoning, decision support.

## When to Load This Skill
Load this skill when the task involves:
- Exploring a topic from multiple angles before a decision
- Generating pro/con arguments for a strategy or idea
- Devil's advocate analysis
- Structured debate output for a proposal or position
- Stress-testing an idea by constructing the strongest counterarguments
- Research tasks that benefit from adversarial reasoning
- Any task where balanced, multi-perspective analysis is needed

## Capabilities
1. **Two-agent debate** — generates FOR and AGAINST arguments separately
2. **Structured rounds** — opening statement → argument → rebuttal → closing
3. **AI judging** — scores each side on logic, evidence quality, and persuasiveness
4. **Decision support** — produces a balanced final verdict with nuance
5. **Topic flexibility** — works on business decisions, product choices, policy, strategy

## Output Format
```json
{
  "topic": "...",
  "position_a": {
    "stance": "FOR / PRO",
    "opening": "...",
    "key_arguments": ["arg 1", "arg 2", "arg 3"],
    "closing": "..."
  },
  "position_b": {
    "stance": "AGAINST / CON",
    "opening": "...",
    "key_arguments": ["arg 1", "arg 2", "arg 3"],
    "closing": "..."
  },
  "verdict": {
    "winner": "Position A / Position B / Draw",
    "score_a": 7.5,
    "score_b": 8.0,
    "reasoning": "...",
    "recommendation": "..."
  }
}
```

## Instructions for Agent
1. Take the topic and construct a FOR position with the strongest possible arguments.
2. Construct an AGAINST position with the strongest possible counterarguments.
3. Do not strawman either side — steel-man both positions.
4. Evaluate which side made the stronger case based on logic and evidence.
5. Score both sides 1-10 on: argument strength, evidence quality, consistency.
6. Provide a nuanced recommendation that acknowledges both sides.

## Constraints
- Both positions must have at least 3 substantial arguments — no one-liners.
- The judge must be neutral — do not let personal bias affect scoring.
- The verdict must explain WHY one position won, not just declare it.
- If the topic has no clear winner, say "Draw" with balanced reasoning.

## Keywords (for task matching)
debate, argue, pros and cons, devil's advocate, two sides, for against,
analysis, reasoning, decision support, evaluate, should we, is it better,
compare options, make a case
