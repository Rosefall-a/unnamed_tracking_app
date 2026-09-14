from __future__ import annotations

import json
import logging
import secrets
import time
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from src.core.auth import SESSION_COOKIE, hash_password, hash_token
from src.core.config import settings
from src.core.crypto import decrypt_secret
from src.core.oidc import OidcConfig, begin_oidc, oauth, register_oidc_provider
from src.database.models.auth import UserSession
from src.database.models.oidc_settings import OidcSettings
from src.database.models.user import User
from src.database.session import get_db

# ...
