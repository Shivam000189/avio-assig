"""Root convenience entry point for database seeding.

Usage:
    python seed.py
"""

import asyncio
from scripts.seed import main

if __name__ == "__main__":
    asyncio.run(main())
