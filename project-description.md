# Cinema Monitor

## Objective
Create a reusable Python library that can discover Cinema City screenings, fetch the associated SVG seat maps, parse them into a structured model, and recommend optimal available seats. This replaces the brittle screenshot-based approach from Phase 1.

## Architecture Overview
1. **Screening Discovery & Calendar Sweep**
   - Input: Movie page URL (or parameters to construct it).
   - Process:
     - Iterate across all relevant dates (e.g., next N days/weekends) by mutating the `at` parameter in the movie URL.
     - For each date, fetch the HTML, locate `<div class="qb-movie-info-column">`, extract each `<a.btn.btn-primary.btn-lg>` with its visible time and `data-url`.
   - Output: `Screening` descriptors containing the human-readable time, metadata, booking URL (`data-url`), and the date they belong to.
   - Notes: if a date has no shows, the Cinema City site redirects to the next available date—this should be detected and logged so the iterator can skip duplicates or halt cleanly.

2. **Seat Map Fetcher**
   - Input: Booking URL from the screening descriptor.
   - Process: Plain HTTP GET (no browser automation) to retrieve the seat-map HTML, extract the `<svg id="svg-seatmap">` fragment.
   - Output: SVG text ready for parsing. Handles timeouts, retries, and non-200 responses with explicit exceptions.

3. **Seat Map Parser & Domain Model**
   - Converts the SVG DOM into domain entities:
     - `Seat` (row, seat label, grid coordinates from the `s` attribute, availability state).
     - `SeatRow` / `SeatMap` aggregates that offer convenient row/column lookups.
   - Parses `aria-description` (`"row: 3 seat: 8 - Available"`) and `<text>` nodes, validating consistency.
   - Supports statuses: Available, Occupied, Wheelchair, Unknown.
   - Logs & skips malformed nodes without failing the entire parse.

4. **Seat Selection Engine**
   - Operates solely on the domain model (no HTML).
   - Filters seats by availability and wheelchair inclusion.
   - Scores single seats and contiguous blocks using configurable weights:
     - Horizontal distance from the hall centre.
     - Row band preference (e.g., middle rows).
     - Penalties for front/back or extreme sides.
   - Sliding-window search for contiguous blocks of size _N_ using the discrete X index from the `s` attribute.
   - Outputs JSON-serialisable recommendations (row number, seat labels, indices, score).

5. **Public API Layer**
   - High-level functions to:
     - Sweep dates for the configured range and discover screenings that meet time/day filters.
     - Fetch + parse seat maps for selected screenings.
     - Request top-N seat suggestions for a given party size.
   - Encapsulates networking & parsing, returning simple dicts/lists for downstream consumers (CLI, Telegram bot, etc.).

6. **Testing Strategy**
   - Use saved HTML fixtures for:
     - Screening list pages.
     - Seat-map SVGs representing empty halls, crowded halls, no contiguous blocks, wheelchair rows, etc.
   - Unit-test each layer:
     - HTML parsing for screenings.
     - SVG parsing invariants (row/seat labels, `s` attribute interpretation).
     - Seat-scoring heuristics and contiguous block detection.
   - Add regression tests for malformed data (missing `aria-description`, mismatched seat numbers).

## Configuration & Extensibility
- Environment variables still handle secrets for Telegram integration, but the new seat library is parameterised via function arguments (movie URL, scoring weights, wheelchair policies).
- Hall geometry assumptions (row order, centre columns) are configurable to handle different cinemas/layouts.
- Clear module boundaries enable future swaps (e.g., caching layer for HTTP, alternative scoring strategies).

## Implementation Roadmap
1. Design & implement the domain model plus parsing layer using static fixtures.
2. Build screening discovery and seat-map fetching components with resilient HTTP handling.
3. Implement the seat-selection engine with configurable scoring + contiguous block search.
4. Expose a public API that orchestrates discovery → fetch → parse → recommend.
5. Integrate the Telegram/scheduler workflow once the core library is battle-tested.
