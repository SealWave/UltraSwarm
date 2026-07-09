# E-commerce Swarm Global Knowledge Base

## Emoji Policy
- **Global Constraint**: Emojis are strictly FORBIDDEN in the following outputs:
  - Product names and listings
  - Product descriptions (including HTML descriptions)
  - Blog posts, articles, and long-form written content
  - Meta titles and meta descriptions (SEO metadata)
  - Ad copy (Google Ads, Meta Ads body/headlines, TikTok Ads copy)
  - Banner briefs and visual asset directions
- **Exceptions**: Emojis are ONLY permitted in organic social media post captions (e.g., Instagram feed captions, TikTok descriptions, Pinterest descriptions) to match platform culture.

## Product Type Copywriting & Pricing Strategy
- **SaaS / Subscription Products**:
  - Focus on recurring value, time-to-value (how fast they see results), solving workflow problems, scalability, and ease of onboarding.
  - Structure listings with a focus on features, technical specifications, subscription tiers (e.g., monthly vs annual), free trial periods, and integration options.
  - Position pricing around ongoing value (ROAS/ROI) and monthly/annual options rather than one-time transactions.
  - Tone should be professional, value-driven, structured, and modern.
- **Physical / Regular Products**:
  - Focus on product aesthetics, tangible specs (dimensions, materials, weight), shipping policies, physical variations (color, size), and product packaging.
  - Structure listings with emotional hooks, pain-point agitation, physical product features, and physical trust badges/guarantees.
  - Position pricing around bundle offers, compare-at pricing, and retail markup.
  - Tone should be sensory, lifestyle-oriented, enthusiastic, and customer-focused.
## Dynamic Browser Control Rule

Agents should not rely on hardcoded browser refs or fixed field order. When an
agent needs to browse, source products, or fill an admin page, it should use an
observe-plan-act loop:

1. Observe the current page with an Agent Browser accessibility snapshot.
2. Plan exactly one safe action from the current state and swarm goal.
3. Act through the approved browser action runner.
4. Store useful results in swarm memory.
5. Re-snapshot after navigation or dynamic page changes.

For supplier sourcing, SCOUT should prefer products with real demand signals:
high order count, meaningful review/comment volume, strong rating, cheap source
price, and good resale margin. A perfect rating with very low buys should rank
below a slightly lower rating with much stronger purchase volume.

For admin upload, FORGE should map fields by meaning. Use labels, placeholders,
roles, button text, and nearby context to find product title, description, price,
category, tags, image, and save/publish controls. Do not assume the admin page
uses the same field order every time.
