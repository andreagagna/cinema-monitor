# Tutorial: Extend Seat Scoring (a.k.a. Seat Wizardry 101)

Ever sat in the front row of an IMAX and regretted your life choices? Let’s
teach the monitor to prefer seats more like “Row 10, centre-ish” and less like
“Row 1, bring neck brace”.

## Goal

- Understand how `SeatSelector` scores seats.
- Prototype a new heuristic (aisle preference, anyone?).
- Bake your rule into tests so future contributors don’t break it.

## Ingredients

- `tests/fixtures/seatmaps/` – pre-baked SVGs with different hall layouts.
- `src/seat_selection.py` – the scoring engine.
- A curious mind ✨ (and optionally some coffee).

## Step 1 – Peek Inside SeatSelector

Open `src/seat_selection.py` and skim `SeatSelector._score_seat`. You’ll notice
two components:

```python
column_component = 1 - abs(seat.grid_x - column_center) / column_half_range
row_component = 1 - abs(seat.grid_row - row_center) / row_half_range
score = (
    column_component * config.column_weight
    + row_component * config.row_weight
)
```

> **Checkpoint:** With `row_weight=0.8` and `column_weight=0.2`, which matters
> more? (Hint: Who needs horizontal perfection when you can avoid the front row?)

## Step 2 – Create a Playground Script

Add `playground/score_demo.py` (or run interactively):

```python
from pathlib import Path

from src.seat_map import SeatMapParser
from src.seat_selection import SeatScoringConfig, SeatSelector

fixture = Path("tests/fixtures/seatmaps/example.svg").read_text()
seat_map = SeatMapParser().parse(fixture)

selector = SeatSelector(
    seat_map,
    SeatScoringConfig(row_weight=0.7, column_weight=0.3, include_wheelchair=False),
)

for suggestion in selector.best_single_seats(top_n=5):
    print(suggestion)
```

Run it:

```bash
uv run python playground/score_demo.py
```

> **Checkpoint:** Do the top rows match your intuition? If they’re hugging the
> aisle when you expected centre seats, time to adjust weights.

## Step 3 – Inject a Fancy Heuristic

Let’s boost aisle seats (grid positions near min/max X). Add this helper inside
`SeatSelector`:

```python
def _aisle_bonus(self, seat: Seat) -> float:
    if seat.grid_x in {self.seat_map.min_grid_x, self.seat_map.max_grid_x}:
        return 0.1
    if seat.grid_x in {self.seat_map.min_grid_x + 1, self.seat_map.max_grid_x - 1}:
        return 0.05
    return 0.0
```

Then tweak `_score_seat`:

```python
return (
    column_component * self.config.column_weight
    + row_component * self.config.row_weight
    + self._aisle_bonus(seat)
)
```

> **Humour interlude:** Congratulations, you’ve just invented “Seat Spice™”.

## Step 4 – Write a Test Before the Magic Fades

Add a test (e.g., `tests/test_seat_selection.py::test_aisle_bonus`):

```python
def test_aisle_bonus_prefers_edges(sample_seat_map):
    selector = SeatSelector(
        sample_seat_map,
        SeatScoringConfig(row_weight=0.5, column_weight=0.5),
    )
    suggestions = selector.best_single_seats(top_n=2)
    assert suggestions[0].grid_positions[0] in {
        sample_seat_map.min_grid_x,
        sample_seat_map.max_grid_x,
    }
```

> **Checkpoint:** Run `uv run pytest tests/test_seat_selection.py -k aisle` and
> celebrate the green checkmark. No confetti? Consider adding some to your shell.

## Stretch Goals

1. **Dynamic wheelchair toggle:** Expose `include_wheelchair` via an env var or
   CLI flag so users can opt-in without code changes.
2. **Per-seat logging:** Add optional logging of component scores to help debug
   “why did you pick *that* seat?!” moments. Bonus points for emoji bars.
3. **Doc update:** Record your new heuristic in `docs/reference.md` under the
   SeatSelector section so future contributors understand the intent.

Now go forth and make future you thankful for better seats. 🪑😎
