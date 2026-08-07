repo: EvaUnit09/Moody
branch: main

## Last sync
date: 2026-08-07T02:12:53Z

### Updated in this project
- Built the landing page (Moody.dc.html) from the repo's concept doc: single mood search bar, no genre filters, results grid with poster/title/year/one-line reason — matching the RAG-then-rerank product described in docs/architecture.md.
- Result shape (title, year, reason) follows backend/app/models.py's MovieRecommendation fields (poster art swapped for placeholder slots since no live posters exist yet).
- Demo search is a static keyword-matched mock (frontend has no working backend yet) standing in for the real /recommend call in frontend/src/api.ts.

## Screen map
| Project screen | Repo files |
| --- | --- |
| Moody.dc.html | docs/architecture.md, frontend/src/App.tsx, frontend/src/api.ts, backend/app/models.py |
