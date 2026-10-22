# Git workflow (keep it boring)

```bash
git clone <repo> && cd finpulse-ai
git checkout -b m3/impact-engine      # <member>/<task>
# ...work, small commits...
git pull --rebase origin main
git push -u origin m3/impact-engine   # open PR -> main, 1 reviewer
```
- Commit message: `area: what` e.g. `impact: add sign-aware path scoring`.
- Don't commit `.env`, API keys, `node_modules`, `.venv`.
- Do commit `data/cache/*.csv` and `data/llm_cache/*.json` (demo must work offline).
- Merge to `main` early and often. Broken `main` = stop and fix first.
- Hour 0 sync: agree on `contracts/`. After that, only additive changes.
