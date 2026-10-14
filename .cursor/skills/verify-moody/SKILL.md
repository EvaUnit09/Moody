---
name: verify-moody
description: "Drive Moody, the mood-based movie recommender in this repo (Vite UI on 127.0.0.1:5173 plus FastAPI on 127.0.0.1:8000). Use to launch the local stack, prove a user-facing feature in the browser, and capture evidence. Reach for it when a change touches the UI, recommend/popular API behavior a user can see, watchlist, hidden titles, or sort."
---

# Verify Moody

Moody is a web app. The user types a mood, gets up to six movie cards, and can save or hide titles in this browser. A second surface is the HTTP API (`POST /recommend`, `GET /popular`, `GET /health`). UI proof goes through the browser. `curl` checks readiness and side effects. A curl of `/recommend` does not prove the screen.

The feature map in `features/README.md` is the source of which journeys exist. Driving one convenient path does not cover the others.

One stack only. Backend and frontend ports are `8000` and `5173`. The backend uses the shared Supabase session pooler (15 client slots, shared with any other Moody process). A second uvicorn on another port still opens pool connections. If `launch` reports a port already in use, stop. Do not kill that process. It is not this run.

`http://127.0.0.1:5173` localStorage is shared with any other visit to that origin, including the user's dev server. Do not clear `moody-watchlist`, `moody-passed`, `moody-exclude-passed`, `moody-recent-moods`, or `movierec:popular-cache`. A journey that writes one of those keys saves the previous value and restores it before cleanup.

## Launch

From the repo root:

```bash
./.cursor/skills/verify-moody/scripts/moody-verify.sh launch
```

That starts a detached session (`setsid`) so the servers keep running after `launch` returns:

- `uv run --python 3.13 --with-requirements requirements.txt uvicorn app.main:app --host 127.0.0.1 --port 8000` with working directory `backend/` (so `backend/.env` loads). `DB_POOL_MIN_SIZE=0` and `DB_APPLICATION_NAME=moody-verify`.
- `npm run dev -- --host 127.0.0.1 --port 5173 --strictPort` with working directory `frontend/`.

Ready means all three of these, not merely that a process exists:

- `GET http://127.0.0.1:8000/health` returns `{"status":"ok"}`. Uvicorn does not listen until startup has opened the pool and warmed popular.
- `GET http://127.0.0.1:8000/popular` returns JSON whose `results` array has at least one movie.
- `GET http://127.0.0.1:5173/` returns HTML containing `<title>Moody</title>`.

`launch` waits up to 240 seconds (`MOODY_VERIFY_READY_TIMEOUT`). The first run may spend most of that installing Python packages. Logs are `$MOODY_VERIFY_STATE_DIR` (default `/tmp/moody-verify`) `backend.log` and `frontend.log`. If you read a log, do not copy a database URL or API key into the chat. `launch` is safe to repeat: if this script already owns both ports and doctor would pass, it prints doctor output and does not start another pair.

Requires `uv`, `npm`, `curl`, `lsof`, `python3`, and `backend/.env`. `frontend/.env.local` may set `VITE_API_URL` only to `http://localhost:8000` or `http://127.0.0.1:8000`. Unset uses the same default in `frontend/src/api.ts`. CORS allows this frontend origin.

## Doctor

```bash
./.cursor/skills/verify-moody/scripts/moody-verify.sh doctor
```

Run this first whenever something looks off. It is read-only. It passes only when the recorded pids are alive, those pids (or their children) own ports 8000 and 5173, health is ok, `/popular` has at least one result, and the frontend title is Moody. Any other listener fails the check. Do not drive an instance doctor rejects.

## Drive

Use the Cursor browser tools against `http://127.0.0.1:5173`: `browser_navigate`, then `browser_lock`, then `browser_snapshot`, `browser_click`, `browser_fill`, and `browser_take_screenshot`. Unlock when finished. Playwright against the same URL is fine if those names and roles stay the same.

Prefer accessible names from the feature file. The mood field is the only `textbox`. It has no label. Its placeholder rotates every 3.2 seconds (`something slow and melancholic...`, `a movie that feels like a rainy sunday...`, `high energy, no thinking required...`, `a heist that goes almost too smoothly...`), so do not address it by placeholder.

Stable controls:

- Brand button named `Moody` returns home and aborts an in-flight search.
- `Open watchlist` opens the dialog named `My List`. `Close watchlist` closes it.
- Submit button is named `Search`, or `Thinking...` while a request is in flight. It stays disabled while the textbox is empty or a search is running.
- Mood chips are named `Search for <mood> movies`. Starter moods include `slow & melancholic`, `date night`, `cozy rainy night`.
- Home shelf heading text is `popular right now`. Arrow buttons are `Scroll left` and `Scroll right`.
- After a successful search, the heading text is `matches for “<query>”`, sort is the radiogroup `Sort results`, and each card may expose `Add to watchlist`, `Pass on this recommendation`, and `Find more like this`.
- Carousel cards do not expose `Add to watchlist` or `Pass on this recommendation`.

`POST /recommend` allows 10 requests per minute per client IP. Spend them on purpose. Wait until `Thinking...` is gone and either result cards or the text `Nothing quite matches that` is visible. Do not sleep a fixed length and guess.

Read `features/README.md`, then the feature file, before driving. Start from home (no `?q=`) unless that file's preconditions say otherwise.

## Evidence

Write proof under `.cursor/skills/verify-moody/artifacts/<feature-id>/`. Cleanup must not delete that directory.

For a UI journey, capture both the action and the resulting state:

- An accessibility snapshot taken after the action.
- A screenshot that shows the Moody brand and the resulting state.
- The feature id and the entry point used, in a short `notes.txt` next to those files.

Also check the side effect, not only the pixels:

- Popular shelf: a title from a poster alt (`<title> poster`) or `.card-title` also appears in `GET /popular` `results`. The carousel links in the accessibility snapshot are unnamed.
- Search: the address bar is `?q=` plus the query, and the heading quotes that query. A non-empty grid shows at least one card title and a `reason` line.
- Watchlist: the dialog lists the title, and `localStorage['moody-watchlist']` contains that `tmdb_id`. Restore the previous value afterward.
- Hide: the card disappears, a toast named region `Notifications` contains `Hidden`, and `localStorage['moody-passed']` contains the id. Restore afterward.
- Sort: the on-screen title order matches the selected radio (`Highest rated`, `Newest`, or `Title A–Z`) using the ratings and years visible on the cards. No second `/recommend` is required; sorting is local.

Do not prove a journey by calling React state setters or by posting to `/recommend` alone. There is no test-only endpoint. External systems (Supabase, OpenAI embeddings, Anthropic rerank, TMDB posters and watch links) are the real production path. A missing poster or empty provider row can still be a successful recommendation. A 500 or the recovery sentence is not a successful search.

## Cleanup

```bash
./.cursor/skills/verify-moody/scripts/moody-verify.sh cleanup
```

This terminates only the pid trees recorded at launch, then deletes `/tmp/moody-verify` (or `MOODY_VERIFY_STATE_DIR`). It does not remove `artifacts/`. Run it after a failed launch too, so a half-started uv or vite process does not keep the ports or a pool connection. If a journey saved and restored localStorage, cleanup does not touch those keys.

## Helpers

`./.cursor/skills/verify-moody/scripts/moody-verify.sh` with `launch`, `doctor`, or `cleanup`. State pids and logs live in `/tmp/moody-verify`. Proof lives in `.cursor/skills/verify-moody/artifacts/`.
