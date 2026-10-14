# Hide a title

The user passes on a recommendation. That card leaves the grid immediately. Later searches can omit the saved ids when "don't show hidden" is on.

## Sub-features

- `hide-pass` removes the card and stores its TMDB id in this browser.
- `hide-undo` puts that id back within the toast lifetime.
- `hide-exclude` sends the saved ids on the next search only while the checkbox is on.

## How to get to it (user POV)

- On a result card, activate `Pass on this recommendation`.
- In the `Notifications` region, activate `Undo` on the `Hidden` toast.
- After at least one title has been passed, use the checkbox `don't show hidden` beside the mood textbox. It is on unless the user turned it off.

## Driving it with the Cursor browser

Preconditions:

- Doctor is ok.
- A successful search with at least two cards is on screen.
- Read `localStorage['moody-passed']` and `localStorage['moody-exclude-passed']` first. Restore both in a `finally` step.
- Passing does not call `/recommend`. The next search does, and it counts against the 10 per minute limit. Prove `hide-exclude` only when a second request is affordable. If it is not, report `hide-exclude` as not run and why. Do not claim the checkbox worked because the card disappeared locally.

- **Pass.** Remember the card title and, from its TMDB link `https://www.themoviedb.org/movie/<id>`, the id. Click `Pass on this recommendation` on that card. The title is gone from the grid. The region `Notifications` contains `Hidden` and a button `Undo`. `localStorage['moody-passed']` is a JSON array containing that id.
- **Checkbox appears.** The checkbox `don't show hidden` is now in the search form. It is checked when `moody-exclude-passed` is missing or any value other than `false`.
- **Undo.** Click `Undo` before 6 seconds pass. The id is no longer in `moody-passed`. Run the same search again only if you still have rate-limit budget and need the card back on screen. Undo restores the id even when the grid does not repaint the card until the next results render.
- **Exclude.** With the checkbox checked and at least one id stored, run a new search. The request body includes `exclude_tmdb_ids` containing that id. With the checkbox unchecked, the id stays in `moody-passed` and the next request omits `exclude_tmdb_ids`. Observe the request. Do not infer it from the checkbox graphic alone.
- **Restore.** Write back the original passed list and exclude flag.
- **Proof.** Save `artifacts/hide-title/hidden.aria.txt` and `artifacts/hide-title/hidden.png` while the toast is visible and the title is gone. `notes.txt` names `hide-pass` and entry point `result card`.

## Gotchas

- The pass control is not on carousel cards.
- The toast lasts about 6 seconds. After it is gone, Undo is gone. The id remains stored.
- More than 100 stored ids makes the next `/recommend` a 422, and the UI takes the recovery path. A long local list can fail a later search for that reason.
- The grid also drops passed ids from the current results even when the server still returned them. Local disappearance does not prove `hide-exclude`.
- Turning the checkbox off does not delete `moody-passed`.
