from __future__ import annotations

import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw

from src.seat_map import Seat, SeatMap, SeatStatus
from src.seat_selection import SeatBlockSuggestion


class SeatMapRenderer:
    """Render SeatMap data into PNG previews highlighting recommended seats."""

    AVAILABLE_COLOR = "#4CAF50"
    OCCUPIED_COLOR = "#7A7A7A"
    WHEELCHAIR_COLOR = "#1E88E5"
    UNKNOWN_COLOR = "#9E9E9E"
    RECOMMENDED_COLOR = "#FF9800"
    BACKGROUND_COLOR = "#11121A"
    BORDER_COLOR = "#0F172A"
    RECOMMENDED_BORDER = "#FFFFFF"

    def __init__(
        self,
        *,
        output_dir: str | Path | None = None,
        seat_size: int = 26,
        seat_gap: int = 6,
        margin: int = 20,
    ) -> None:
        self.seat_size = seat_size
        self.seat_gap = seat_gap
        self.margin = margin
        base_dir = (
            Path(output_dir) if output_dir else Path(tempfile.gettempdir()) / "cinema-monitor"
        )
        self.output_dir = base_dir / "renders"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._status_colors = {
            SeatStatus.AVAILABLE: self.AVAILABLE_COLOR,
            SeatStatus.OCCUPIED: self.OCCUPIED_COLOR,
            SeatStatus.WHEELCHAIR: self.WHEELCHAIR_COLOR,
            SeatStatus.UNKNOWN: self.UNKNOWN_COLOR,
        }

    def render(self, seat_map: SeatMap, suggestion: SeatBlockSuggestion) -> str:
        """Render the given seat map, highlighting seats inside suggestion."""
        if not seat_map.seats:
            raise ValueError("Cannot render seat map without seats.")

        width = self._dimension(seat_map.min_grid_x, seat_map.max_grid_x)
        height = self._dimension(seat_map.min_grid_row, seat_map.max_grid_row)

        image = Image.new("RGB", (width, height), self.BACKGROUND_COLOR)
        draw = ImageDraw.Draw(image)

        highlighted = {(suggestion.row_number, seat_num) for seat_num in suggestion.seat_numbers}

        for seat in seat_map.seats:
            box = self._seat_box(seat_map, seat)
            fill = self._status_colors.get(seat.status, self.UNKNOWN_COLOR)
            outline = self.BORDER_COLOR

            if (seat.row_number, seat.seat_number) in highlighted:
                fill = self.RECOMMENDED_COLOR
                outline = self.RECOMMENDED_BORDER

            draw.rectangle(box, fill=fill, outline=outline, width=2)

        filename = f"seatmap_{datetime.utcnow():%Y%m%d%H%M%S}_{uuid.uuid4().hex}.png"
        output_path = self.output_dir / filename
        image.save(output_path, format="PNG")
        return str(output_path)

    def _dimension(self, min_value: int, max_value: int) -> int:
        span = max_value - min_value + 1
        span = max(span, 1)
        return self.margin * 2 + span * self.seat_size + max(span - 1, 0) * self.seat_gap

    def _seat_box(self, seat_map: SeatMap, seat: Seat) -> Tuple[int, int, int, int]:
        col = seat.grid_x - seat_map.min_grid_x
        row = seat.grid_row - seat_map.min_grid_row

        x0 = self.margin + col * (self.seat_size + self.seat_gap)
        y0 = self.margin + row * (self.seat_size + self.seat_gap)
        x1 = x0 + self.seat_size
        y1 = y0 + self.seat_size
        return (x0, y0, x1, y1)
