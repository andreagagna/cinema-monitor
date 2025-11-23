from pathlib import Path

from src.seat_map import SeatMapParser
from src.seat_selection import SeatScoringConfig, SeatSelector

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def build_selector(include_wheelchair: bool = False) -> SeatSelector:
    svg = load_fixture("seatmap_sample.svg")
    seat_map = SeatMapParser().parse(svg)
    config = SeatScoringConfig(include_wheelchair=include_wheelchair)
    return SeatSelector(seat_map, config)


def test_best_single_seats_prioritizes_center():
    selector = build_selector()
    suggestions = selector.best_single_seats(top_n=2)
    assert len(suggestions) == 2
    assert suggestions[0].seat_numbers[0] in {11, 12}


def test_best_blocks_finds_contiguous_sets():
    selector = build_selector()
    blocks = selector.best_blocks(size=2, top_n=2)
    assert blocks
    assert blocks[0].seat_numbers == [11, 12]


def test_including_wheelchair_allows_extra_seats():
    selector = build_selector(include_wheelchair=True)
    seats = selector.best_single_seats(top_n=5)
    wheelchair_found = any(seat_block.labels == ["10"] for seat_block in seats)
    assert wheelchair_found
