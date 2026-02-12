"""Seed data for sample users."""

import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserContext

# Path to sample data files
SAMPLE_DATA_DIR = Path(__file__).parent.parent / "config" / "sample_data"

logger = logging.getLogger(__name__)


def load_sample_users() -> list:
    """Load sample users from JSON config file."""
    users_file = SAMPLE_DATA_DIR / "users.json"
    if not users_file.exists():
        logger.warning(f"Sample users file not found: {users_file}")
        return []

    with open(users_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("users", [])


async def seed_sample_users(db: AsyncSession) -> None:
    """Seed sample users from JSON config file."""
    sample_users = load_sample_users()

    if not sample_users:
        logger.warning("No sample users found to seed")
        return

    users_created = 0
    for user_data in sample_users:
        user_id = user_data.get("user_id")
        if not user_id:
            logger.warning("Sample user missing user_id, skipping")
            continue

        # Check if user already exists
        result = await db.execute(
            select(UserContext).where(UserContext.user_id == user_id)
        )
        if result.scalar_one_or_none():
            logger.debug(f"User {user_id} already exists, skipping")
            continue

        user = UserContext(
            user_id=user_id,
            profile=user_data.get("profile"),
            product_summaries=user_data.get("product_summaries"),
            behavioral_summary=user_data.get("behavioral_summary"),
        )
        db.add(user)
        users_created += 1
        logger.info(f"Created sample user: {user_id}")

    if users_created > 0:
        await db.commit()
        logger.info(f"Seeded {users_created} sample user(s) successfully!")
    else:
        logger.info("All sample users already exist, skipping")
