"""Fallback artwork for games that do not have stored cover art."""

import asyncio
import hashlib
from html import escape
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.games import ALLOWED_ASSET_KINDS, _DATA_ROOT, _get_game_or_404
from src.core.auth import get_current_user
from src.database.models.user import User
from src.database.session import get_db
from src.helpers.asset_previews import ensure_preview, preview_path
from src.helpers.save_game_asset import ASSET_FILENAMES, AssetKind

router = APIRouter(
    prefix="/api/game",
    tags=["game"],
    dependencies=[Depends(get_current_user)],
)


# the app's own palette (see frontend styles/ui.css), so a cover with no artwork
# reads as part of the app: flat charcoal, one accent, the same type and spacing
_SURFACE = "#222222"
_BACKGROUND = "#141414"
_BORDER = "#2b2b2b"
_TEXT = "#f2f2f2"
_DIM = "#9c9c9c"
_ACCENT = "#d68a34"
_FONT = "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"


def _wrap_title(title: str, width: int = 17, lines: int = 3) -> list[str]:
    """Break a title into at most `lines` lines of about `width` characters."""
    words = title.split()
    out: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width or not current:
            current = candidate
        else:
            out.append(current)
            current = word
    if current:
        out.append(current)
    if len(out) > lines:
        out = out[:lines]
        out[-1] = out[-1][: max(1, width - 1)].rstrip() + "\u2026"
    return [line[: width + 6] for line in out] or ["Unknown Game"]


def _mix(top: str, base: str, share: float) -> str:
    """`share` of the colour `top` over `base`, as a hex colour."""
    a = [int(top[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(base[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x * share + y * (1 - share)):02x}" for x, y in zip(a, b))


def _default_cover_svg(game_id: UUID, title: str, plain: bool = False) -> str:
    """Build a lightweight SVG cover for a game with no artwork, drawn the way the
    app draws its own cards: a flat charcoal panel with a thin border, a small
    accent label, the title set large and bold, and a faint first letter. Only the
    amount of accent in the panel varies by game. With `plain` the title is left
    out, for pages that print it themselves."""
    name = title.strip() or "Unknown Game"
    safe_title = escape(name)
    digest = hashlib.sha256(str(game_id).encode("utf-8")).hexdigest()
    warmth = 0.05 + (int(digest[8:12], 16) % 100) / 100 * 0.07
    top = _mix(_ACCENT, _SURFACE, warmth)
    initial = escape(next((c for c in name if c.isalnum()), "?").upper())

    lines = _wrap_title(name, width=14)
    size = 64 if max(len(line) for line in lines) <= 10 else 54
    title_block = ""
    if not plain:
        top_y = 742 - (len(lines) - 1) * (size + 8)
        tspans = "".join(
            f'<tspan x="52" y="{top_y + i * (size + 8)}">{escape(line)}</tspan>'
            for i, line in enumerate(lines)
        )
        label_y = top_y + (len(lines) - 1) * (size + 8) + 52
        title_block = (
            f'<text fill="{_TEXT}" font-family="{_FONT}" font-size="{size}" '
            f'font-weight="800" letter-spacing="-1">{tspans}</text>'
            f'<text x="52" y="{label_y}" fill="{_DIM}" font-family="{_FONT}" '
            'font-size="22" font-weight="600" letter-spacing="3">NO COVER ART</text>'
        )

    initial_y = 560 if plain else 520
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 900" role="img" aria-label="{safe_title} default cover">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0.5" y2="1">
      <stop offset="0" stop-color="{top}"/>
      <stop offset="1" stop-color="{_BACKGROUND}"/>
    </linearGradient>
  </defs>
  <rect width="600" height="900" fill="url(#bg)"/>
  <text x="560" y="{initial_y}" text-anchor="end" fill="{_TEXT}" fill-opacity="{'.07' if plain else '.05'}" font-family="{_FONT}" font-size="560" font-weight="800">{initial}</text>
  <text x="52" y="96" fill="{_ACCENT}" font-family="{_FONT}" font-size="22" font-weight="700" letter-spacing="4">GAME</text>
  <rect x="52" y="116" width="40" height="3" rx="1.5" fill="{_ACCENT}"/>
  {title_block}
  <rect x=".5" y=".5" width="599" height="899" fill="none" stroke="{_BORDER}"/>
</svg>"""


_KEEP_AN_HOUR = "private, max-age=3600, must-revalidate"
_KEEP_FOR_GOOD = "private, max-age=31536000, immutable"


def revalidated_file(request: Request, path: Path, media_type: str) -> Response:
    """Artwork the browser keeps, so a page full of covers costs no requests. It is
    replaced in place (a new cover, a refreshed banner) under the same address, which
    is why the page asks for a new address (`?v=`) whenever it changes a picture: that
    address has never been cached, so the new file is fetched at once, and it can then
    be kept for good. An address without `v` is kept for an hour and then checked (the
    tag changes whenever the file does, so an unchanged file answers "not modified"
    without being sent again)."""
    stat = path.stat()
    tag = f'"{stat.st_mtime_ns:x}-{stat.st_size:x}"'
    headers = {
        "Cache-Control": _KEEP_FOR_GOOD if "v" in request.query_params else _KEEP_AN_HOUR,
        "ETag": tag,
    }
    if request.headers.get("if-none-match") == tag:
        return Response(status_code=304, headers=headers)
    return FileResponse(path, media_type=media_type, headers=headers)


@router.get("/{game_id}/assets/{asset_kind}")
async def get_game_asset_with_fallback(
    request: Request,
    game_id: UUID,
    asset_kind: AssetKind,
    # a smaller copy for showing on screen: the stored banner is a 3840 px PNG
    # of several MB, far more than a page needs
    w: int | None = Query(default=None, ge=64, le=4096),
    # a generated cover without the title, for pages that print the title themselves
    plain: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Serve stored artwork (or a resized JPEG of it with `w`), falling back to
    generated cover art when needed."""
    if asset_kind not in ALLOWED_ASSET_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported asset kind '{asset_kind}'. Supported values: {sorted(ALLOWED_ASSET_KINDS)}",
        )

    game = await _get_game_or_404(game_id, db, current_user.id)
    asset_path = (
        _DATA_ROOT
        / str(game.user_id)
        / "games"
        / game.folder_location
        / ASSET_FILENAMES[asset_kind]
    )

    if asset_path.is_file():
        media_type = "image/png"
        if w is not None:
            asset_path, media_type = await asyncio.to_thread(
                ensure_preview,
                asset_path,
                preview_path(_DATA_ROOT / str(game.user_id) / ".cache", str(game_id), asset_kind, w),
                w,
            )
        return revalidated_file(request, asset_path, media_type)

    if asset_kind != "key_art":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_kind}' has not been uploaded for game {game_id}.",
        )

    return Response(
        content=_default_cover_svg(game.id, game.title, plain),
        media_type="image/svg+xml",
        # never kept: this stands in for a picture that is not there yet, and one kept
        # by the browser would go on showing in its place after the real one arrives
        headers={"Cache-Control": "private, no-cache"},
    )