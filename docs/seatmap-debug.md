++ docs/seatmap-debug.md
# Seat Map Debugging Notes

This file records the investigation that led to the “API-first” seat-map
fetcher. Keep it around while the new approach settles.

## What Was Going Wrong

1. Our `data-url` values pointed to `https://tickets.cinemacity.cz/api/order/{id}`,
   but the SPA renders seat maps at `/order/{id}` (no `api`). Even after we
   normalised the URL and used Playwright, some showings never populated
   `svg#svg-seatmap` before our timeout, so we constantly retried and logged
   `No seat map SVG present`.
2. Increasing `navigation_timeout_ms` helped occasionally, but the root issue
   was that the SPA loads seat data via JSON APIs. The SVG shell is injected
   quickly, but the seat `<g aria-description="…">` nodes arrive only after the
   client fetches and merges:
   - `/api/presentations/{id}` → metadata (venue id, seatplan id, etc.).
   - `/api/seats/seatplanV2?venueId=...&seatplanId=...` → layout/coordinates.
   - `/api/seats/seats-statusV2?presentationId=...` → seat availability.
   Waiting for DOM nodes was unreliable and slow.

## Findings in the HAR File (`network.har`)

- Filtered entries containing `seat` / `plan` (lines ~660+) and saw two key
  endpoints:
  ```
  https://tickets.cinemacity.cz/api/seats/seatplanV2?venueId=80&seatplanId=3
  https://tickets.cinemacity.cz/api/seats/seats-statusV2?presentationId=84044&venueTypeId=1&isReserved=1
  ```
- The seat plan response (`seatplanV2`) is a nested JSON structure:
  - `S[section].G[group].R[row].S[seat]` with seat coordinates (`rd`) and labels.
  - Example seat entry: `{"rd": {"cx": 600, "cy": -30}, "n": "21"}`.
- The seat status response (`seats-statusV2`) is a flat dictionary:
  - Keys like `1_10_1` (section_seat_row) whose values are always `0` in the
    captures we have. It does **not** encode availability, so we can’t rely on
    it for “free vs taken” state.
- Presentation metadata endpoint (`/api/presentations/{id}`) revealed `venueId`,
  `seatplanId`, `venueTypeId` – everything we needed to call the other APIs.
- Conclusion: we can build the SVG ourselves by combining seat plan + seat
  status, rather than waiting for the SPA DOM.

## Strategy

1. Continue normalising `/api/order/{id}` → `/order/{id}` for consistency.
2. Extract `presentation_id` from the URL.
3. Call Cinema City’s API trio:
   - `/api/presentations/{id}?referralMiniSiteId=0`
   - `/api/seats/seatplanV2?venueId={venueId}&seatplanId={seatplanId}`
   - `/api/seats/seats-statusV2?presentationId={id}&venueTypeId={venueTypeId}&isReserved=1`
4. Merge plan + status into our own SVG string with `<g aria-description="…">`
   nodes that match the original HTML structure used by `SeatMapParser`.
5. Keep Playwright as a fallback (in case APIs change or authentication is
   required) but rely on the API path for normal operation.

## Implementation

- `SeatMapFetcher` changes:
  - Added `_extract_presentation_id`, `_fetch_presentation_metadata`,
    `_fetch_seatplan`, `_fetch_seat_status`, `_build_svg_from_plan`, and a
    shared `_http_get`.
  - `fetch_svg` now attempts the API path first (fast, deterministic). Only if
    that fails do we fall back to Playwright.
  - Playwright path still dismisses cookies and waits for `g[aria-description]`
    for resilience.
- Tests:
  - Added JSON fixtures (`presentation_api.json`, `seatplan_api.json`,
    `seat_status_api.json`) and updated `tests/test_seatmap_fetcher_module.py`
    to cover API synthesis, `/api/order` normalization, and browser fallback.
- Docs/notes:
  - This file summarises the discovery; once the approach stabilises we can
    integrate the relevant parts into `docs/architecture.md` / `docs/reference.md`.

If the SPA or APIs evolve, revisit this doc to trace what changed and whether
we need to adjust the fetcher again.

## Current Considerations & Options (Dec 2025)

- **Seats-status API is not useful**: `seats-statusV2` always returns `0` for
  every seat, so it doesn’t encode availability. The only place we’ve seen
  accurate seat statuses is the live SVG DOM after it has finished loading.
- **Seat locking uses `PUT /api/seats/lock-seat`**: the HAR from clicking a seat
  shows a `PUT` with `PresentationId`, `VenueId`, coordinates, etc., but the
  response body is empty. Without the session cookies / captcha token, there’s
  no public API endpoint that returns the “seat taken” state for all seats.
- **Options**:
  1. Stick with Playwright for final seat states (still the most reliable) and
     use the API only for geometry.
  2. Attempt to reverse-engineer the seat-lock flow (hard; requires replicating
     auth tokens and possibly captcha).
  3. Treat the API-generated SVG as a fallback when Playwright fails completely,
     understanding that it can’t distinguish available vs occupied.

- **Action plan**: Keep Playwright as the primary source of truth for seat
  availability. The API-generated SVG can help when the SPA refuses to load or
  when we want deterministic layout data, but we shouldn’t expect it to encode
  live availability. If we discover a reliable API for statuses in the future,
  we can revisit and simplify the flow.
