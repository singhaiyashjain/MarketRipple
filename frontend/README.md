# FinPulse frontend

React + Vite + Tailwind, with a 3D "constellation" graph (3d-force-graph + three.js), dark theme.

## Run (two terminals)
```
# terminal 1 - backend
cd backend
.venv\Scripts\activate        # Windows (macOS/Linux: source .venv/bin/activate)
uvicorn app.main:app --reload --port 8000

# terminal 2 - frontend
cd frontend
npm install
npm run dev                   # http://localhost:5173  (proxies /api -> :8000)
```
UI only, no backend: put `VITE_USE_MOCK=true` in `frontend/.env.local`.

## Using the graph
- Every variable is a white star; halo colour = effect (green benefit, red pressure, violet mixed). The event is the ringed star.
- Drag = rotate, scroll = zoom, right-drag = pan, ＋/－ and Orbit buttons for touch.
- Click a star: camera flies to it, its links light up, info card opens (what drives it / what it affects, influence score).
  Click a chip in the card to travel to a linked star. Reasoning and evidence appear in the right-hand panel.
- "See the graph from this star" puts the camera inside the star looking at its neighbours. Drag to look around, scroll changes the field of view.
- Click a link for its evidence; pick a path on the left to frame the whole chain. Esc resets.

## Code map
- `src/components/ImpactGraph3D.jsx` - the 3D scene, selection/camera logic (same props + `fit/relayout/exportPng` handle as the old 2D graph)
- `src/components/OrbCard.jsx` - floating star info card + POV button
- `src/lib/space.js` - starfield, nebula, orbs, labels, link sign sprites
- `src/components/ImpactGraph.jsx` - the old 2D cytoscape graph, unused; swap the import in `App.jsx` to go back
- Colours live in `tailwind.config.js` (dark tokens) and `src/lib/format.js` (`EFFECT_COLOR`)
