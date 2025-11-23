from __future__ import annotations

import enum
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class SeatStatus(enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    WHEELCHAIR = "wheelchair"
    UNKNOWN = "unknown"

    @classmethod
    def from_description(cls, text: str) -> "SeatStatus":
        lowered = text.strip().lower()
        if "wheelchair" in lowered:
            return cls.WHEELCHAIR
        if "available" in lowered:
            return cls.AVAILABLE
        if "occupied" in lowered:
            return cls.OCCUPIED
        return cls.UNKNOWN


@dataclass(frozen=True)
class Seat:
    row_number: int
    seat_number: int
    label: str
    status: SeatStatus
    grid_x: int
    grid_row: int
    metadata: Dict[str, str] = field(default_factory=dict)

    def is_available(self, include_wheelchair: bool = False) -> bool:
        if self.status == SeatStatus.AVAILABLE:
            return True
        if include_wheelchair and self.status == SeatStatus.WHEELCHAIR:
            return True
        return False


@dataclass
class SeatRow:
    row_number: int
    grid_index: int
    seats: List[Seat]


@dataclass
class SeatMap:
    seats: List[Seat]
    rows: Dict[int, SeatRow]
    min_grid_x: int
    max_grid_x: int
    min_grid_row: int
    max_grid_row: int

    @classmethod
    def from_seats(cls, seats: Iterable[Seat]) -> "SeatMap":
        seat_list = sorted(seats, key=lambda s: (s.grid_row, s.grid_x))
        rows: Dict[int, SeatRow] = {}
        min_x = min((seat.grid_x for seat in seat_list), default=0)
        max_x = max((seat.grid_x for seat in seat_list), default=0)
        min_row = min((seat.grid_row for seat in seat_list), default=0)
        max_row = max((seat.grid_row for seat in seat_list), default=0)

        for seat in seat_list:
            row = rows.setdefault(
                seat.row_number,
                SeatRow(row_number=seat.row_number, grid_index=seat.grid_row, seats=[]),
            )
            row.seats.append(seat)

        for row in rows.values():
            row.seats.sort(key=lambda s: s.grid_x)

        return cls(
            seats=seat_list,
            rows=rows,
            min_grid_x=min_x,
            max_grid_x=max_x,
            min_grid_row=min_row,
            max_grid_row=max_row,
        )

    def available_seats(self, include_wheelchair: bool = False) -> List[Seat]:
        return [seat for seat in self.seats if seat.is_available(include_wheelchair)]


class SeatMapParser:
    """Parse Cinema City SVG seat maps into SeatMap structures."""

    _aria_pattern = re.compile(
        r"row:\s*(?P<row>\d+)\s+seat:\s*(?P<seat>\d+)\s*-\s*(?P<status>[A-Za-z ]+)",
        re.IGNORECASE,
    )

    def parse(self, svg_markup: str) -> SeatMap:
        soup = BeautifulSoup(svg_markup, "html.parser")
        viewport = soup.select_one("svg#svg-seatmap g.svg-pan-zoom_viewport")
        if viewport is None:
            raise ValueError("Seat map SVG missing viewport group")

        seats: List[Seat] = []
        for group in viewport.find_all("g", attrs={"aria-description": True}):
            seat = self._parse_seat_group(group)
            if seat:
                seats.append(seat)
        return SeatMap.from_seats(seats)

    def _parse_seat_group(self, group) -> Optional[Seat]:
        aria = group.get("aria-description")
        attrs = group.attrs
        s_attr = group.get("s")
        text_node = group.find("text")

        if not aria or not s_attr or text_node is None:
            return None

        match = self._aria_pattern.search(aria)
        if not match:
            logger.debug("Skipping seat with malformed aria-description: %s", aria)
            return None

        try:
            row = int(match.group("row"))
            seat_number = int(match.group("seat"))
        except ValueError:
            return None

        label = text_node.get_text(strip=True)
        status = SeatStatus.from_description(match.group("status"))

        try:
            _, grid_x, grid_row = (int(part) for part in s_attr.split(","))
        except (ValueError, TypeError):
            logger.debug("Skipping seat with malformed s attribute: %s", s_attr)
            return None

        metadata = {
            key: value for key, value in attrs.items() if key not in {"aria-description", "s"}
        }

        return Seat(
            row_number=row,
            seat_number=seat_number,
            label=label,
            status=status,
            grid_x=grid_x,
            grid_row=grid_row,
            metadata=metadata,
        )
