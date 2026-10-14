# Watchlist

The user saves a recommended movie on this browser and opens it from My List. The list survives reload. It is not an account on the server.

## Sub-features

- `watchlist-add` saves a result card and shows that title in My List.
- `watchlist-remove` removes it from My List and from the heart on the card.
- `watchlist-empty` shows the empty copy when nothing is saved.
- `watchlist-persist` shows the same title after a reload.

## How to get to it (user POV)

- On a result card, activate `Add to watchlist`.
- Activate `Open watchlist` in the header. The dialog title is `My List`.
- Inside the dialog, activate `Remove from watchlist` on a saved card.
- With a non-empty list, the dialog offers `Export JSON` and `Export Text`.

## Driving it with the Cursor browser

Preconditions:

- Doctor is ok.
- A successful mood search is on screen, so result cards exist. Carousel cards cannot be saved.
- Read `localStorage['moody-watchlist']` before changing it. Restore that exact string in a `finally` step, including when the journey fails. If the key was absent, remove it.
- Budget one recommend call to reach the cards if home is showing. Prefer `cozy rainy night`.

- **Empty state.** Only when the saved key is already empty or missing: click `Open watchlist`. The dialog `My List` contains `Your watchlist is empty.` and `Add movies by clicking the heart icon on any result card.` `Export JSON` is absent. Close with `Close watchlist`.
- **Add.** On a result card, click `Add to watchlist`. A status in the region `Notifications` says `Added to watchlist`. The same card's button is now `Remove from watchlist`. The header `Open watchlist` shows a count. Click `Open watchlist`. The dialog lists that card's title and `1 movie`.
- **Stored value.** `localStorage['moody-watchlist']` is a JSON array containing an object whose `tmdb_id` matches the card and whose `title` matches the visible title.
- **Reload.** Reload `http://127.0.0.1:5173/`. Click `Open watchlist`. The dialog still lists that title. This does not require another recommend call.
- **Remove.** In the dialog, click `Remove from watchlist` for that title. The status says `Removed from watchlist`. The dialog then shows `Your watchlist is empty.` Close the dialog.
- **Restore.** Write back the original `moody-watchlist` value before cleanup.
- **Proof.** Save `artifacts/watchlist/added.aria.txt` and `artifacts/watchlist/added.png` while the dialog is open on the added title. `notes.txt` names `watchlist-add` and entry point `result card`.

## Gotchas

- The heart control is not on `popular right now` cards. If `Add to watchlist` is missing, you are on the carousel.
- A storage failure toasts `Couldn't save — storage full` and leaves the previous list in place. That is a failed add.
- Export buttons download a file in the browser. Do not treat a download as the persistence proof. The localStorage read is the proof.
- The dialog closes on Escape and on the backdrop. `Close watchlist` is the handle to use.
- Restoring localStorage after the proof does not by itself update an already open dialog. Restore, then reload or click `Moody`, so the next journey sees the restored list.
