"""Filter declarative integrations at the public host permission boundary."""

from .contracts import Capability, PluginUiDocument
from .ui_placement import place_navigation, place_settings


def filter_ui_document(
    document: PluginUiDocument,
    effective_capabilities: frozenset[str],
) -> PluginUiDocument:
    """Remove host integrations that this installation is not authorized to mount."""

    def permitted(capability: Capability) -> bool:
        return capability.value in effective_capabilities

    navigation_capabilities = {
        "main.sidebar": Capability.FRONTEND_NAVIGATION_MAIN,
        "settings.sidebar": Capability.FRONTEND_NAVIGATION_SETTINGS,
        "administration": Capability.FRONTEND_NAVIGATION_ADMIN,
        "game.context": Capability.FRONTEND_CONTEXT_GAME,
        "media.context": Capability.FRONTEND_CONTEXT_MEDIA,
    }
    context_capabilities = {
        "game": Capability.FRONTEND_CONTEXT_GAME,
        "media": Capability.FRONTEND_CONTEXT_MEDIA,
        "documents": Capability.FRONTEND_CONTEXT_DOCUMENTS,
    }
    extension_capabilities = {
        "app.global": Capability.FRONTEND_OVERLAY,
        "home.replace": Capability.FRONTEND_PAGE_REPLACE_HOME,
    }
    authorized_routes = document.routes if permitted(Capability.FRONTEND_ROUTES) else ()
    authorized_settings = (
        tuple(place_settings(item, effective_capabilities) for item in document.settings_sections)
        if permitted(Capability.FRONTEND_SETTINGS)
        else ()
    )
    authorized_route_ids = {item.id for item in authorized_routes}
    authorized_settings_ids = {item.id for item in authorized_settings}
    return document.model_copy(
        update={
            "native_frontend": (
                document.native_frontend if permitted(Capability.FRONTEND_NATIVE) else None
            ),
            "navigation": tuple(
                place_navigation(item, effective_capabilities)
                for item in document.navigation
                if permitted(navigation_capabilities[item.location.value])
                and (item.route_id is None or item.route_id in authorized_route_ids)
                and (
                    item.settings_section_id is None
                    or item.settings_section_id in authorized_settings_ids
                )
            ),
            "settings_sections": authorized_settings,
            "extensions": tuple(
                item
                for item in document.extensions
                if permitted(
                    extension_capabilities.get(item.slot.value, Capability.FRONTEND_PAGE_EXTEND)
                )
            ),
            "home_widgets": (
                document.home_widgets if permitted(Capability.FRONTEND_HOME_WIDGETS) else ()
            ),
            "themes": document.themes if permitted(Capability.FRONTEND_THEMES) else (),
            "shortcuts": tuple(
                item
                for item in document.shortcuts
                if permitted(Capability.FRONTEND_SHORTCUTS)
                and (item.route_id is None or item.route_id in authorized_route_ids)
                and (item.when_route_id is None or item.when_route_id in authorized_route_ids)
                and (
                    item.action_id is None
                    or all(
                        action.capability is None
                        or action.capability.name.value in effective_capabilities
                        for action in document.actions
                        if action.id == item.action_id
                    )
                )
            ),
            "overlays": (document.overlays if permitted(Capability.FRONTEND_OVERLAY) else ()),
            "dialog_contributions": (
                document.dialog_contributions if permitted(Capability.FRONTEND_DIALOG) else ()
            ),
            "contextual_actions": tuple(
                item
                for item in document.contextual_actions
                if permitted(context_capabilities[item.location.value])
            ),
            "document_readers": (
                document.document_readers
                if permitted(Capability.FRONTEND_CONTEXT_DOCUMENTS)
                and permitted(Capability.DOCUMENTS_READ)
                else ()
            ),
            "routes": authorized_routes,
            "page_replacements": tuple(
                item
                for item in document.page_replacements
                if permitted(Capability(f"frontend.page.replace.{item.page.value}"))
            ),
        }
    )
