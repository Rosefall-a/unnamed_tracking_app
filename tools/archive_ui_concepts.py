"""Build the portable, reproducible reference gallery without changing its sources."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


def main() -> None:
    """Package both preserved gallery sources and their offline instructions."""
    assets = Path(__file__).resolve().parents[1] / "wiki/docs/assets/ui-redevelopment"
    with ZipFile(assets / "concept-reference.zip", "w", compression=ZIP_DEFLATED) as archive:
        for name in ("concepts.html", "concept-source.html", "concept-reference.md"):
            entry = ZipInfo(name, date_time=(2026, 10, 4, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, (assets / name).read_bytes())


if __name__ == "__main__":
    main()
