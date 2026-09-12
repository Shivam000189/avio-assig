"""Prisma client lifecycle management.

Provides a module-level Prisma client and async helpers for connecting and
disconnecting during the application lifespan.  If the database is unreachable
at startup the error is logged but the app continues to serve traffic so that
non-DB endpoints (e.g. /health) remain available.

Phase 2 note: once models are defined, consider enforcing a hard failure on
startup if the DB connection cannot be established.
"""

import logging

from prisma import Prisma

logger = logging.getLogger(__name__)

prisma = Prisma()


async def connect_db() -> None:
    """Open the Prisma connection pool.

    Logs success or failure.  A failed connection does **not** raise —
    the application stays up so health-check endpoints can still respond.
    """
    try:
        await prisma.connect()
        logger.info("Database connection established.")
    except Exception as exc:
        logger.error("Failed to connect to the database: %s", exc)


async def disconnect_db() -> None:
    """Close the Prisma connection pool gracefully."""
    try:
        if prisma.is_connected():
            await prisma.disconnect()
            logger.info("Database connection closed.")
    except Exception as exc:
        logger.error("Error disconnecting from the database: %s", exc)
