"""Plugin documentation reads remain bounded and never import package code."""

import io
import zipfile

from src.plugin_api.management_auth import management_scope
from src.plugin_api.package_metadata import package_readme


def test_missing_readme_has_no_fabricated_documentation():
    with zipfile.ZipFile(io.BytesIO(), "w") as archive:
        assert package_readme(archive) is None


def test_readme_is_case_insensitive_and_bounded():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("payload/README.md", b"x" * (128 * 1024 + 100))
    with zipfile.ZipFile(buffer) as archive:
        assert package_readme(archive) == "x" * (128 * 1024)


def test_documentation_management_token_scope_is_read_only():
    assert management_scope("GET", "/api/plugins/example.ui-api/details") == "plugins.read"
    assert management_scope("POST", "/api/plugins/example.ui-api/details") is None
