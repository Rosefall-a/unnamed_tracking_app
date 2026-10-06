"""World thumbnails stay bounded even for widely separated region files."""

from PIL import Image

from src.features.world_map.thumbnail import generate_world_thumbnail


def test_sparse_world_thumbnail_stays_within_the_pixel_limit(tmp_path):
    world = tmp_path / "world"
    region = world / "region"
    region.mkdir(parents=True)
    header = b"\x00\x00\x02\x01" + bytes(4092)
    (region / "r.0.0.mca").write_bytes(header)
    (region / "r.16.0.mca").write_bytes(header)
    output = tmp_path / "thumbnail.png"
    assert generate_world_thumbnail(world, output)
    with Image.open(output) as image:
        assert max(image.size) <= 512
        assert image.getpixel((0, 0)) == (94, 168, 122, 255)
        assert image.getpixel((image.width - 1, 0)) == (94, 168, 122, 255)


def test_world_without_readable_chunks_has_no_thumbnail(tmp_path):
    (tmp_path / "region").mkdir()
    (tmp_path / "region" / "r.0.0.mca").write_bytes(b"incomplete header")
    output = tmp_path / "thumbnail.png"
    assert generate_world_thumbnail(tmp_path, output) is False
    assert not output.exists()
