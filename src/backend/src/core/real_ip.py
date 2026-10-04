"""Effective production Nginx real-IP configuration."""

from __future__ import annotations

import ipaddress
import re
from typing import Any

from src.core.env_handler import EnvConfigHandler

DEFAULT_REAL_IP_HEADER = "X-Forwarded-For"
DEFAULT_TRUSTED_PROXIES = ("127.0.0.1/32", "::1/128")

REAL_IP_PRESETS: dict[str, dict[str, Any]] = {
    "local": {
        "label": "Local/private ranges",
        "values": (
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
            "169.254.0.0/16",
            "fc00::/7",
            "fe80::/10",
        ),
    },
    "cgnat": {
        "label": "CGNAT / VPS ranges",
        "values": ("100.64.0.0/10",),
    },
    "cloudflare": {
        "label": "Cloudflare proxy ranges",
        "values": (
            "103.21.244.0/22",
            "103.22.200.0/22",
            "103.31.4.0/22",
            "104.16.0.0/13",
            "104.24.0.0/14",
            "108.162.192.0/18",
            "131.0.72.0/22",
            "141.101.64.0/18",
            "162.158.0.0/15",
            "172.64.0.0/13",
            "173.245.48.0/20",
            "188.114.96.0/20",
            "190.93.240.0/20",
            "197.234.240.0/22",
            "198.41.128.0/17",
            "2400:cb00::/32",
            "2606:4700::/32",
            "2803:f800::/32",
            "2405:b500::/32",
            "2405:8100::/32",
            "2a06:98c0::/29",
            "2c0f:f248::/32",
        ),
    },
}


def validate_real_ip_header(value: str) -> str:
    value = str(value).strip()
    if not value or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("NGINX_REALIP_HEADER must be a valid HTTP header name.")
    return value


def validate_trusted_proxies(value: str) -> str:
    normalized: list[str] = []
    for token in str(value).split():
        try:
            canonical = str(ipaddress.ip_network(token, strict=False))
        except ValueError as exc:
            raise ValueError(f"Invalid trusted proxy address or CIDR: {token}") from exc
        if canonical not in normalized:
            normalized.append(canonical)
    return " ".join(normalized)


def get_real_ip_presets() -> dict[str, dict[str, Any]]:
    return {
        key: {"label": value["label"], "values": list(value["values"])}
        for key, value in REAL_IP_PRESETS.items()
    }


def get_effective_real_ip_config(
    handler: EnvConfigHandler,
    persisted_header: str | None,
    persisted_trusted_proxies: str | None,
) -> dict[str, str]:
    header = (
        handler.get("NGINX_REALIP_HEADER")
        if handler.has("NGINX_REALIP_HEADER")
        else (persisted_header or DEFAULT_REAL_IP_HEADER)
    )
    if handler.has("NGINX_REALIP_TRUSTED_PROXIES"):
        trusted = handler.get("NGINX_REALIP_TRUSTED_PROXIES")
    elif persisted_trusted_proxies and str(persisted_trusted_proxies).strip():
        trusted = persisted_trusted_proxies
    else:
        trusted = " ".join(DEFAULT_TRUSTED_PROXIES)
    return {
        "header": validate_real_ip_header(str(header)),
        "trusted_proxies": validate_trusted_proxies(str(trusted)),
    }
