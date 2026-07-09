# SKILL: Email Drafting Agent
**Agent ID:** `email_drafting_agent`
**Source:** 500-AI-Agents / 05-email-drafting-agent
**Domain:** communication
**Best For:** Writing professional emails — follow-ups, outreach, proposals, confirmations, apologies, announcements.

## When to Load This Skill
Load this skill when the task involves:
- Drafting any type of professional email
- Writing follow-up emails after demos, meetings, or proposals
- Cold outreach to clients, partners, or vendors
- Internal communication emails (announcements, requests, updates)
- Formal correspondence requiring a specific tone
- Any task where the output is an email ready to send

## Capabilities
1. **Context analysis** — extracts purpose, key points, and call-to-action from raw context
2. **Tone adaptation** — adjusts to: professional, friendly, formal, assertive, empathetic
3. **Recipient awareness** — tailors language for client, internal team, executive, vendor, etc.
4. **Complete output** — produces subject line + greeting + body + closing + signature placeholder
5. **Conciseness** — keeps email bodies under 200 words unless depth is required

## Output Format
```
Subject: [subject line]

[Greeting],

[Body paragraph 1 — context/hook]
[Body paragraph 2 — key points]
[Body paragraph 3 — call to action]

[Closing],
[Signature placeholder]
```

## Instructions for Agent
1. First identify: purpose of the email, recipient type, desired tone, key message.
2. Write a subject line that is specific and action-oriented (not generic).
3. Open with context or a hook relevant to the recipient.
4. State key points clearly — one idea per paragraph.
5. End with a single, clear call to action.
6. Keep total word count under 250 unless the task specifies a longer format.
7. Match the tone to the recipient — never use casual slang for executives.

## Constraints
- Never add invented facts about the recipient or company.
- Always include a clear CTA — an email without a next step is incomplete.
- Subject line must be under 60 characters.
- Avoid filler phrases like "I hope this email finds you well."

## Keywords (for task matching)
email, draft email, write email, follow-up, outreach, correspondence,
message, compose, professional email, reply, communication
