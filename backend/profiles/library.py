"""File-backed repository for validated profile definitions."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from backend.ai.providers.factory import get_provider
from backend.profiles.builder import ProfileBuilder
from backend.profiles.schemas import ProfileLibrary


class ProfileLibraryRepository:
    """Loads a validated JSON library, or creates it with the configured LLM."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> ProfileLibrary:
        with self.path.open("r", encoding="utf-8") as handle:
            return ProfileLibrary.model_validate(json.load(handle))

    def save(self, library: ProfileLibrary) -> ProfileLibrary:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(library.model_dump(mode="json"), handle, indent=2)
            handle.write("\n")
        temporary.replace(self.path)
        return library

    async def generate_and_save(self) -> ProfileLibrary:
        library = await ProfileBuilder(get_provider(role="profile_builder")).generate()
        return self.save(library)

    async def load_or_generate(self) -> ProfileLibrary:
        if self.path.exists():
            return self.load()
        return await self.generate_and_save()

    def load_or_generate_sync(self) -> ProfileLibrary:
        """Convenience entry point for setup scripts outside an active event loop."""
        return asyncio.run(self.load_or_generate())
