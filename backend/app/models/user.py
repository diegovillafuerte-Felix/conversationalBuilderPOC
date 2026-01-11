"""User context ORM model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserContext(Base):
    """User context - pre-computed user data for conversation context."""

    __tablename__ = "user_contexts"

    user_id: Mapped[str] = mapped_column(String(100), primary_key=True)

    # Profile: {name, preferredName, language, timezone, memberSince, kycLevel}
    profile: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Product summaries by product type
    # {remittances: {...}, credit: {...}, wallet: {...}, topups: {...}, billPay: {...}}
    product_summaries: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Natural language behavioral summary for prompt injection
    behavioral_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<UserContext {self.user_id}>"

    def get_preferred_name(self) -> str:
        """Get the user's preferred name or fall back to name."""
        return self.profile.get("preferredName") or self.profile.get("name", "Usuario")

    def get_language(self) -> str:
        """Get the user's preferred language."""
        return self.profile.get("language", "es")
