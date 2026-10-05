"""Bounded display metadata from packages; this never loads plugin code."""

import zipfile


def package_readme(archive: zipfile.ZipFile) -> str | None:
    name = next(
        (
            name
            for name in archive.namelist()
            if name.lower() in {"payload/readme.md", "payload/readme.txt"}
        ),
        None,
    )
    if name is None:
        return None
    with archive.open(name) as source:
        return source.read(128 * 1024).decode("utf-8", errors="replace")
