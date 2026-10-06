"""Area-wide permissions for joining built-in navigation headers.

Folder names are presentation metadata. They never create narrower permissions
or inherit a grant from ordinary navigation registration.
"""

from .contracts import Capability, UiNavigationContribution, UiSettingsContribution

SIDEBAR_GROUPS = ("Your library", "Keep track")
SETTINGS_GROUPS = {
    "account": ("Account",),
    "preferences": ("Preferences", "Library", "Information"),
    "administration": ("Server management",),
}
SETTINGS_PLACEMENT_CAPABILITIES = {
    "account": Capability.FRONTEND_PLACEMENT_ACCOUNT,
    "preferences": Capability.FRONTEND_PLACEMENT_PREFERENCES,
    "administration": Capability.FRONTEND_PLACEMENT_ADMIN,
}


def placement_group(group: str, groups: tuple[str, ...], allowed: bool) -> str:
    """Keep custom headers, but require approval before joining a built-in one."""
    matched = next((label for label in groups if label.casefold() == group.casefold()), None)
    return (matched if allowed else "Extensions") if matched else group


def place_navigation(
    item: UiNavigationContribution, capabilities: frozenset[str]
) -> UiNavigationContribution:
    """Resolve main or settings navigation without changing its owned target."""
    if item.location.value == "settings.sidebar":
        area = item.area or ("administration" if item.visibility.admin_only else "preferences")
        groups = SETTINGS_GROUPS[area]
        required = SETTINGS_PLACEMENT_CAPABILITIES[area]
    elif item.location.value in {"main.sidebar", "administration"}:
        groups = SIDEBAR_GROUPS
        required = Capability.FRONTEND_PLACEMENT_SIDEBAR
    else:
        return item
    return item.model_copy(update={
        "group": placement_group(item.group, groups, required.value in capabilities),
    })


def place_settings(
    item: UiSettingsContribution, capabilities: frozenset[str]
) -> UiSettingsContribution:
    """A grant covers every built-in header and folder within its settings area."""
    area = item.area or ("administration" if item.visibility.admin_only else "preferences")
    return item.model_copy(update={
        "group": placement_group(
            item.group, SETTINGS_GROUPS[area],
            SETTINGS_PLACEMENT_CAPABILITIES[area].value in capabilities,
        ),
    })
