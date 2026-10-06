"""The legacy adapter is explicit, limited, and never makes new plugins work on old hosts."""

from uuid import uuid4

import pytest
from test_plugin_api_contracts import manifest_data

from src.plugin_api.compatibility import legacy_plugin_allowed
from src.plugin_api.contracts import (
    CompatibilityStatus,
    PluginManifest,
    evaluate_manifest_compatibility,
)
from src.plugin_api.lifecycle import plugin_contributions_active


@pytest.mark.parametrize("sdk_range", ["^1.0.0", "=1.0.0", ">=1.0.0,<1.1.0"])
def test_shipped_legacy_reference_can_run_with_limited_sdk_support(sdk_range):
    manifest = PluginManifest.model_validate(
        {
            **manifest_data(sdk_range=sdk_range),
            "plugin_id": "example.ui-api",
        }
    )
    assert manifest.api_contract_version == "1.0.0"
    assert (
        evaluate_manifest_compatibility(manifest, "1.1.0", "2.1.0").status
        == CompatibilityStatus.COMPATIBLE
    )


def test_legacy_adapter_never_bypasses_application_or_future_sdk_requirements():
    for overrides in ({"application_version_range": "^3.0.0"}, {"sdk_version_range": "^2.0.0"}):
        manifest = PluginManifest.model_validate(
            {**manifest_data(), "plugin_id": "example.ui-api", **overrides}
        )
        assert (
            evaluate_manifest_compatibility(manifest, "1.1.0", "2.1.0").status
            == CompatibilityStatus.INCOMPATIBLE
        )


def test_existing_identity_and_runtime_qualification_are_required():
    plugin = {
        "plugin_id": "thirdparty.existing",
        "installation_id": str(uuid4()),
        "api_contract_version": "1.0.0",
        "enabled": True,
        "compatible": True,
        "status": "running",
        "health": "healthy",
    }
    assert legacy_plugin_allowed(plugin["plugin_id"], plugin)
    assert not legacy_plugin_allowed("example.any-new-example")
    assert not plugin_contributions_active(plugin)
    assert plugin_contributions_active({**plugin, "legacy_compatibility": True})
    assert not plugin_contributions_active(
        {**plugin, "legacy_compatibility": True, "installation_id": "invalid"}
    )
    assert not plugin_contributions_active(
        {**plugin, "legacy_compatibility": True, "enabled": False}
    )


def test_explicit_new_contract_cannot_run_on_old_host_even_with_adapter():
    manifest = PluginManifest.model_validate({**manifest_data(), "api_contract_version": "1.1.0"})
    assert (
        evaluate_manifest_compatibility(manifest, "1.0.0", "2.1.0", allow_legacy=True).status
        == CompatibilityStatus.INCOMPATIBLE
    )
