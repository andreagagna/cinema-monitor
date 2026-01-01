# Seat Map Renderer

The Cinema Monitor now renders a PNG preview for every seat recommendation,
highlighting the suggested seats so Telegram alerts can include a visual aid.

## Module Overview

- **Location:** `src/seatmap_renderer.py`
- **Entry point:** `SeatMapRenderer.render(seat_map, suggestion) -> str`
- **Dependencies:** Pillow (installed via the existing dependencies)

`SeatMapRenderer` consumes the `SeatMap` object already produced by
`SeatMapParser` and the specific `SeatBlockSuggestion` that scored highest for a
screening. It does **not** fetch or parse the SVG again—reducing network load
and ensuring the visuals exactly match the ranked seats.

## Colour Legend

| Seat type        | Colour     | Hex      |
| ---------------- | ---------- | -------- |
| Available        | Cinema green | `#4CAF50` |
| Occupied         | Dark grey  | `#7A7A7A` |
| Wheelchair       | Blue       | `#1E88E5` |
| Recommended seat | Orange highlight with white outline | `#FF9800` |

Unknown seat types fall back to a muted grey to ensure they remain visible
without drawing attention away from the target seats.

## Output Directory

Rendered files are written to `<tmp>/cinema-monitor/renders`, where `<tmp>` is
the operating system temporary directory. This keeps screenshots transient by
default, but you can override the directory by passing `output_dir` to the
renderer if you need to archive results.

Each filename follows `seatmap_<timestamp>_<uuid>.png` so concurrent runs never
clash. The absolute path returned by `render` is used by `MonitorScheduler` to
attach the preview to Telegram notifications.

## Customising the Renderer

The renderer constructor exposes `seat_size`, `seat_gap`, and `margin`
parameters. Increasing `seat_size` results in larger squares for auditoriums
with fewer rows, while tweaking `seat_gap` adds breathing room between seats.
The background colour and seat palette can also be changed by subclassing
`SeatMapRenderer` and overriding the class constants.

```python
from src.seatmap_renderer import SeatMapRenderer

renderer = SeatMapRenderer(output_dir="/tmp/cinema-monitor-custom")
preview_path = renderer.render(seat_map, suggestion)
print(f"Seat map stored at {preview_path}")
```

When integrating outside of `MonitorScheduler`, make sure the returned path
persists for as long as your notifier needs it (e.g., avoid deleting the file
before a message is sent).
