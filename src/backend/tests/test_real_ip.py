from src.core.env_handler import EnvConfigHandler
from src.core.real_ip import (
    DEFAULT_REAL_IP_HEADER,
    DEFAULT_TRUSTED_PROXIES,
    get_effective_real_ip_config,
    get_real_ip_presets,
    validate_real_ip_header,
    validate_trusted_proxies,
)


def test_default_real_ip_config_is_loopback_only():
    config = get_effective_real_ip_config(EnvConfigHandler({}), None, None)
    assert config["header"] == DEFAULT_REAL_IP_HEADER
    assert config["trusted_proxies"] == " ".join(DEFAULT_TRUSTED_PROXIES)


def test_persisted_real_ip_config():
    config = get_effective_real_ip_config(
        EnvConfigHandler({}),
        "CF-Connecting-IP",
        "127.0.0.1/32 100.64.0.0/10",
    )
    assert config["header"] == "CF-Connecting-IP"
    assert config["trusted_proxies"] == "127.0.0.1/32 100.64.0.0/10"


def test_environment_overrides_persisted():
    handler = EnvConfigHandler(
        {
            "NGINX_REALIP_HEADER": "X-Forwarded-For",
            "NGINX_REALIP_TRUSTED_PROXIES": "10.0.0.0/8",
        }
    )
    config = get_effective_real_ip_config(handler, "CF-Connecting-IP", "127.0.0.1/32")
    assert config["trusted_proxies"] == "10.0.0.0/8"


def test_presets_are_backend_owned():
    presets = get_real_ip_presets()
    assert {"local", "cgnat", "cloudflare"} == set(presets)
    assert "100.64.0.0/10" in presets["cgnat"]["values"]


def test_invalid_values():
    try:
        validate_real_ip_header("bad;include /tmp/evil;")
        raise AssertionError("invalid header unexpectedly accepted")
    except ValueError:
        pass
    try:
        validate_trusted_proxies("10.0.0.0/8;include /tmp/evil;")
        raise AssertionError("invalid proxy list unexpectedly accepted")
    except ValueError:
        pass
