"""Generate or replace the validated profile library before running a simulation."""

import asyncio

from backend.config import settings
from backend.profiles.library import ProfileLibraryRepository


async def main() -> None:
    repository = ProfileLibraryRepository(settings.PROFILE_LIBRARY_PATH)
    library = await repository.generate_and_save()
    print(f"Saved {len(library.profiles)} validated profiles to {repository.path}")


if __name__ == "__main__":
    asyncio.run(main())
