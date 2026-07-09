# ECOM SWARM - Problems & Improvements Backlog

## Current / Resolved Issues
1. **[RESOLVED]** SCOUT agent was not showing source links/URLs for the products it found. (Added `source_url` field to output JSON schema).
2. **[RESOLVED]** SCOUT CLI required manual edits to change the number of products and the specific genre. (Now prompts interactively with defaults).
3. **[RESOLVED]** Browser actions were running invisibly (headless) by default, making it impossible to see the agent working. (Fixed in `browser.py` and `README.md` instructions).

## Improvement Backlog
1. **Store manager product schema needs normalization**
   - The product listing output and the store upload format are not fully aligned.
   - `tools/store_admin.py` expects `description_html`, but `agents/product_agent.py` usually returns `description`.
   - `agents/store_manager_agent.py` should map and validate one shared product schema before upload.

2. **Product sourcing should target real supplier sites instead of generic search queries**
   - Current discovery should rely on DuckDuckGo search results instead of Google snippets.
   - Add supplier-first sourcing paths for places like CJ Dropshipping, Alibaba, and other approved vendor sources.

3. **Add a dedicated custom admin workflow for store uploads**
   - The store manager needs an additional admin mode for the custom ecommerce page.
   - Make the upload logic resilient enough to work from screenshots and accessibility snapshots rather than assuming fixed field positions.

4. **Browser automation needs dynamic control, not fixed command paths**
   - The current browser layer should use browser-use by default, with the Vercel agent-browser flow kept only as a commented fallback.
   - Build a smarter ref-finding strategy using snapshot text, roles, labels, and nearby context.

5. **Add a browser skill/rule/knowledge layer for page-structure adaptation**
   - Create a reusable skill or rule that teaches agents how to find inputs, buttons, and filters from a snapshot even when the layout changes.

6. **Product research output labels should be cleaned up**
   - Standardize output naming so reports follow one clear format across agents and swarms.

7. **Browser search should be less Google-dependent**
   - Add alternative search sources or fallback search logic.
   - Cache successful queries where appropriate.

8. **Improve field detection in browser-based store automation**
   - Add stronger field detection using labels, roles, surrounding text, and page context.

9. **Add schema validation before saving outputs or pushing products**
   - Before calling store upload or saving JSON outputs, validate that required fields exist.

10. **Reduce hardcoded environment assumptions**
    - Add a clearer fallback strategy so the system can work even if only one key is configured.

11. **Improve launch planning quality for the store manager agent**
    - The store manager outputs should include clearer launch order, platform-specific steps, and a custom-admin checklist.

12. **Add more robust product sourcing filters**
    - In product research, add a minimum-volume threshold and a confidence score.
