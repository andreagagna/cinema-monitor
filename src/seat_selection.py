from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List, Sequence

from src.seat_map import Seat, SeatMap


@dataclass
class SeatScoringConfig:
    row_weight: float = 0.5
    column_weight: float = 0.5
    include_wheelchair: bool = False


@dataclass
class SeatBlockSuggestion:
    row_number: int
    seat_numbers: List[int]
    labels: List[str]
    grid_positions: List[int]
    score: float


class SeatSelector:
    def __init__(self, seat_map: SeatMap, config: SeatScoringConfig | None = None):
        self.seat_map = seat_map
        self.config = config or SeatScoringConfig()
        self._column_center = (self.seat_map.min_grid_x + self.seat_map.max_grid_x) / 2
        self._row_center = (self.seat_map.min_grid_row + self.seat_map.max_grid_row) / 2
        self._column_half_range = max(
            (self.seat_map.max_grid_x - self.seat_map.min_grid_x) / 2,
            1,
        )
        self._row_half_range = max(
            (self.seat_map.max_grid_row - self.seat_map.min_grid_row) / 2,
            1,
        )

    def best_single_seats(self, top_n: int = 5) -> List[SeatBlockSuggestion]:
        seats = self.seat_map.available_seats(include_wheelchair=self.config.include_wheelchair)
        seats.sort(
            key=lambda seat: (
                -self._score_seat(seat),
                abs(seat.grid_x - self._column_center),
                abs(seat.grid_row - self._row_center),
            )
        )
        suggestions: List[SeatBlockSuggestion] = []
        for seat in seats[:top_n]:
            suggestions.append(
                SeatBlockSuggestion(
                    row_number=seat.row_number,
                    seat_numbers=[seat.seat_number],
                    labels=[seat.label],
                    grid_positions=[seat.grid_x],
                    score=self._score_seat(seat),
                )
            )
        return suggestions

    def best_blocks(self, size: int, top_n: int = 3) -> List[SeatBlockSuggestion]:
        blocks: List[SeatBlockSuggestion] = []
        for row in self.seat_map.rows.values():
            seats = [
                seat for seat in row.seats if seat.is_available(self.config.include_wheelchair)
            ]
            if not seats:
                continue
            seats.sort(key=lambda seat: seat.grid_x)
            for window in self._consecutive_windows(seats, size):
                score = sum(self._score_seat(seat) for seat in window) / size
                blocks.append(
                    SeatBlockSuggestion(
                        row_number=row.row_number,
                        seat_numbers=[seat.seat_number for seat in window],
                        labels=[seat.label for seat in window],
                        grid_positions=[seat.grid_x for seat in window],
                        score=score,
                    )
                )
        blocks.sort(key=lambda b: b.score, reverse=True)
        return blocks[:top_n]

    def _score_seat(self, seat: Seat) -> float:
        column_component = 1 - abs(seat.grid_x - self._column_center) / self._column_half_range
        row_component = 1 - abs(seat.grid_row - self._row_center) / self._row_half_range

        column_component = max(min(column_component, 1), 0)
        row_component = max(min(row_component, 1), 0)

        return column_component * self.config.column_weight + row_component * self.config.row_weight

    def _consecutive_windows(self, seats: Sequence[Seat], size: int) -> Iterator[Sequence[Seat]]:
        if size <= 0:
            return
        current: List[Seat] = []
        last_x: int | None = None

        for seat in seats:
            if last_x is None or seat.grid_x == last_x + 1:
                current.append(seat)
            else:
                yield from self._slide_windows(current, size)
                current = [seat]
            last_x = seat.grid_x
        if current:
            yield from self._slide_windows(current, size)

    def _slide_windows(self, seats: Sequence[Seat], size: int) -> Iterator[Sequence[Seat]]:
        if len(seats) < size:
            return
        for idx in range(0, len(seats) - size + 1):
            yield seats[idx : idx + size]
