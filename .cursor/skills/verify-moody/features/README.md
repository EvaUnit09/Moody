# Moody verification map

This directory is the maintained source for verifying Moody's user-facing behavior. Read this index, then the feature file for the journey you are proving.

## Baseline preconditions

- Run `./.cursor/skills/verify-moody/scripts/moody-verify.sh launch`, then `doctor`.
- Drive `http://127.0.0.1:5173` only after doctor prints `moody-verify doctor: ok`.
- The backend on port 8000 must be the process that script started (`DB_APPLICATION_NAME=moody-verify`).
- Start each recipe from home (no `?q=` in the URL) unless its preconditions say otherwise.
- Do not clear localStorage. This origin is shared with local dev. Save and restore any key a journey writes.
- Do not start a second stack. Ports 8000 and 5173, and the shared Supabase session pooler, are exclusive to the running instance.

## Driving conventions

- Prefer ARIA roles and accessible names. The mood textbox has no accessible name; it is the only textbox. Ignore its rotating placeholder.
- Use the Cursor browser tools (`browser_snapshot`, `browser_click`, `browser_fill`, `browser_take_screenshot`) against `http://127.0.0.1:5173`.
- Wait for `Thinking...` to leave the Search button before reading results.
- `POST /recommend` allows 10 requests per minute from this IP. A chip click is a search.
- Record the feature id and entry point in `artifacts/<feature-id>/notes.txt`.
- Leave proof files in place when you clean up processes.

## Proof and skip reporting

- Capture the action and the state it produced.
- UI proof is an accessibility snapshot plus a screenshot that shows the Moody brand.
- HTTP side effects are response bodies saved next to the screenshot, with secrets left out. `/popular` and `/recommend` bodies are movie metadata, not credentials.
- localStorage mutations are proven by reading the key, then restored to the value from before the journey.
- If an entry point cannot be reached, report the attempted control and the unmet precondition. Do not mark it verified via a different path.

## Feature entry contract

Each feature file has an H1, one paragraph, then four H2 sections: `Sub-features`, `How to get to it (user POV)`, `Driving it with the Cursor browser`, and `Gotchas`.

## Features

- [Popular shelf](./popular-shelf.md) covers the home carousel: titles from `GET /popular`, and scrolling.
- [Mood search](./mood-search.md) covers the textbox, starter chips, the `?q=` URL, recovery, and going home.
- [Watchlist](./watchlist.md) covers saving a result, the My List dialog, and removal.
- [Sort results](./sort-results.md) covers reordering the current grid without a new search.
- [Hide a title](./hide-title.md) covers passing a card, undo, and the don't-show-hidden checkbox.
