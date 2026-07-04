import asyncio
import logging
import sys

from api.models.db import async_session_factory
from api.services.precompute_service import run_precomputations

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

async def main():
    async with async_session_factory() as db:
        await run_precomputations(db)

if __name__ == "__main__":
    asyncio.run(main())
