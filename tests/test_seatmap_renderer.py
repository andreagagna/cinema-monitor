from pathlib import Path

from PIL import Image, ImageColor

from src.seat_map import Seat, SeatMap, SeatStatus
from src.seat_selection import SeatBlockSuggestion
from src.seatmap_renderer import SeatMapRenderer


def _build_seat(row_number: int, seat_number: int, grid_x: int) -> Seat:
    return Seat(
        row_number=row_number,
        seat_number=seat_number,
        label=str(seat_number),
        status=SeatStatus.AVAILABLE,
        grid_x=grid_x,
        grid_row=row_number,
    )


def test_renderer_highlights_recommendations(tmp_path):
    seats = [
        _build_seat(1, 1, 1),
        _build_seat(1, 2, 2),
    ]
    seat_map = SeatMap.from_seats(seats)
    suggestion = SeatBlockSuggestion(
        row_number=1, seat_numbers=[2], labels=["2"], grid_positions=[2], score=0.95
    )

    renderer = SeatMapRenderer(output_dir=tmp_path)
    image_path = Path(renderer.render(seat_map, suggestion))

    assert image_path.exists()

    image = Image.open(image_path)
    try:
        recommended_seat = seats[1]
        available_seat = seats[0]

        recommended_center = _seat_center(renderer, seat_map, recommended_seat)
        available_center = _seat_center(renderer, seat_map, available_seat)

        recommended_rgb = ImageColor.getrgb(SeatMapRenderer.RECOMMENDED_COLOR)
        available_rgb = ImageColor.getrgb(SeatMapRenderer.AVAILABLE_COLOR)

        assert image.getpixel(recommended_center) == recommended_rgb
        assert image.getpixel(available_center) == available_rgb
    finally:
        image.close()


def _seat_center(renderer: SeatMapRenderer, seat_map: SeatMap, seat: Seat) -> tuple[int, int]:
    x0, y0, x1, y1 = renderer._seat_box(seat_map, seat)
    return (x0 + (renderer.seat_size // 2), y0 + (renderer.seat_size // 2))
