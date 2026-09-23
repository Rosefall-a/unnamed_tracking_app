from src.core.setup_config import SetupConfiguration


def test_environment_tree_is_limited_to_registered_pages():
    config = SetupConfiguration({
        "OIDC__AUTHENTIK__CLIENT_ID": "archive",
        "OIDC__AUTHENTIK__ENABLED": "true",
        "UNREGISTERED__VALUE": "ignored",
    })
    config.register_page("OIDC", "OIDC")
    assert config.tree() == {
        "OIDC": {"authentik": {"client_id": "archive", "enabled": True}}
    }


def test_environment_values_override_form_values_recursively():
    config = SetupConfiguration({
        "OIDC__AUTHENTIK__CLIENT_ID": "from-env",
        "OIDC__AUTHENTIK__SECURITY__REQUIRE_VERIFIED_EMAIL": "false",
    })
    config.register_page("OIDC", "OIDC")
    result = config.apply("OIDC", {
        "authentik": {
            "client_id": "from-form",
            "security": {"require_verified_email": True, "other": "kept"},
        },
        "unrelated": "kept",
    })
    assert result["authentik"]["client_id"] == "from-env"
    assert result["authentik"]["security"]["require_verified_email"] is False
    assert result["authentik"]["security"]["other"] == "kept"
    assert result["unrelated"] == "kept"


def test_setup_mode_can_disable_interactive_setup():
    config = SetupConfiguration({"SETUP_MODE": "false"})
    assert config.setup_enabled() is False
    assert config.setup_enabled("dev") is True
