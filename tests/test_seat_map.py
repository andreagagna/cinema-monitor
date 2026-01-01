from pathlib import Path

from src.seat_map import SeatMapParser, SeatStatus

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parser_builds_seatmap_with_expected_seats():
    svg = load_fixture("seatmap_sample.svg")
    parser = SeatMapParser()
    seat_map = parser.parse(svg)

    assert len(seat_map.seats) == 9
    row1 = seat_map.rows[1]
    assert len(row1.seats) == 3
    assert row1.seats[0].seat_number == 5
    assert row1.seats[0].status == SeatStatus.AVAILABLE
    assert row1.seats[1].status == SeatStatus.OCCUPIED

    available = seat_map.available_seats()
    assert {seat.seat_number for seat in available} == {5, 7, 11, 12, 13, 16}


def test_parser_includes_wheelchair_when_requested():
    svg = load_fixture("seatmap_sample.svg")
    parser = SeatMapParser()
    seat_map = parser.parse(svg)

    seats = seat_map.available_seats(include_wheelchair=True)
    wheelchair = [seat for seat in seats if seat.status == SeatStatus.WHEELCHAIR]
    assert len(wheelchair) == 1


def test_parser_falls_back_when_viewport_missing():
    svg = """
    <svg id="svg-seatmap" viewBox="0 0 100 100">
      <g s="1,1,1" aria-description="row: 1 seat: 1 - Available">
        <text>1</text>
      </g>
      <g s="1,2,1" aria-description="row: 1 seat: 2 - Occupied">
        <text>2</text>
      </g>
    </svg>
    """
    parser = SeatMapParser()
    seat_map = parser.parse(svg)

    assert len(seat_map.seats) == 2
    statuses = {seat.seat_number: seat.status for seat in seat_map.seats}
    assert statuses[1] == SeatStatus.AVAILABLE
    assert statuses[2] == SeatStatus.OCCUPIED
