"""Bounded, portable keyboard bindings shared by preferences and plugin declarations."""

import re

MODIFIERS = ("CtrlOrMeta", "Ctrl", "Meta", "Alt", "Shift")
NAMED_KEYS = (
    "ArrowUp",
    "ArrowDown",
    "ArrowLeft",
    "ArrowRight",
    "Enter",
    "Escape",
    "Space",
    "Tab",
    "Home",
    "End",
    "PageUp",
    "PageDown",
    "Delete",
    "Backspace",
    "Plus",
)


def normalize_shortcut_key(value: str) -> str:
    """Accept a single combination; no expressions, sequences or executable targets."""
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError("Shortcut keys must be bounded keyboard combinations.")
    parts = [part.strip() for part in value.strip().split("+")]
    raw = parts.pop()
    key = next((item for item in NAMED_KEYS if item.lower() == raw.lower()), None)
    if key is None and (
        re.fullmatch(r"[a-z0-9/?.,;\[\]\-='`]", raw, re.IGNORECASE)
        or re.fullmatch(r"F(?:[1-9]|1\d|2[0-4])", raw, re.IGNORECASE)
    ):
        key = raw.upper()
    normalized = [
        next((item for item in MODIFIERS if item.lower() == part.lower()), None) for part in parts
    ]
    conflicting_modifiers = "CtrlOrMeta" in normalized and bool({"Ctrl", "Meta"} & set(normalized))
    if (
        key is None
        or None in normalized
        or len(set(normalized)) != len(normalized)
        or conflicting_modifiers
    ):
        raise ValueError("Use a key with optional CtrlOrMeta, Ctrl, Meta, Alt and Shift modifiers.")
    return "+".join([*(item for item in MODIFIERS if item in normalized), key])


def validate_shortcut_overrides(value: object) -> dict:
    """Keep unavailable plugin overrides so reinstalling retains the user's choices."""
    if not isinstance(value, dict) or len(value) > 512:
        raise ValueError("Shortcut overrides must contain at most 512 entries.")
    result = {}
    for identifier, options in value.items():
        if not isinstance(identifier, str) or not re.fullmatch(
            r"[a-z0-9][a-z0-9:._-]{0,299}", identifier
        ):
            raise ValueError("Invalid shortcut identifier.")
        if not isinstance(options, dict) or set(options) - {"enabled", "keys", "enabled_order"}:
            raise ValueError("Shortcut overrides accept only enabled, keys and enabled_order.")
        if "enabled" in options and not isinstance(options["enabled"], bool):
            raise ValueError("Shortcut enabled must be true or false.")
        if "enabled_order" in options and (
            not isinstance(options["enabled_order"], int)
            or isinstance(options["enabled_order"], bool)
            or not 0 <= options["enabled_order"] <= 9_007_199_254_740_991
        ):
            raise ValueError("Shortcut activation order must be a nonnegative safe integer.")
        entry = dict(options)
        if "keys" in entry:
            if not isinstance(entry["keys"], list) or not 1 <= len(entry["keys"]) <= 4:
                raise ValueError(
                    "Provide one to four shortcut combinations, or disable the shortcut."
                )
            entry["keys"] = list(
                dict.fromkeys(normalize_shortcut_key(key) for key in entry["keys"])
            )
        result[identifier] = entry
    return result
