from __future__ import annotations

import time

from sqlalchemy import BigInteger, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class GlobalSettings(Base):
	"""Singleton row for global project behavior and future settings."""

	__tablename__ = "global_settings"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
	app_name: Mapped[str] = mapped_column(String(200), nullable=False, default="Unnamed Tracking App")
	default_currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
	timezone: Mapped[str] = mapped_column(String(100), nullable=False, default="UTC")
	allow_registration: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
	created_at: Mapped[int] = mapped_column(BigInteger, nullable=False, default=time.time)
	updated_at: Mapped[int] = mapped_column(
		BigInteger,
		nullable=False,
		default=time.time,
		onupdate=time.time,
	)
