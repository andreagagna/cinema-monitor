from src.seat_counter import SeatDetectionConfig, count_seats_from_image


def create_test_image(tmp_path, pixels):
    from PIL import Image

    img = Image.new("RGB", (len(pixels[0]), len(pixels)))
    for y, row in enumerate(pixels):
        for x, color in enumerate(row):
            img.putpixel((x, y), color)
    path = tmp_path / "test.png"
    img.save(path)
    return str(path)


def test_count_seats_simple_blob(tmp_path):
    green = (76, 175, 80)
    other = (0, 0, 0)
    pixels = [
        [other, green, green],
        [other, green, green],
        [other, other, other],
    ]
    path = create_test_image(tmp_path, pixels)
    cfg = SeatDetectionConfig(target_color=green, tolerance=0, min_blob_size=1)
    count, sizes = count_seats_from_image(path, cfg)
    assert count == 1
    assert list(sizes) == [4]
