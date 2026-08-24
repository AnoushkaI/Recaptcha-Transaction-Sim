"""LLM profile-library generation and schema validation."""

from __future__ import annotations

import json
import re

from backend.ai.providers.base import BaseLLMProvider
from backend.profiles.prompts import PROFILE_BUILDER_SYSTEM_PROMPT, build_single_profile_prompt
from backend.profiles.schemas import PROFILE_IDS, ProfileDefinition, ProfileLibrary

_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


class ProfileGenerationError(RuntimeError):
    """The provider response could not be converted into a valid profile library."""


class ProfileBuilder:
    """Builds a complete library from small, independently validated LLM responses."""

    def __init__(self, provider: BaseLLMProvider, max_retries: int = 2) -> None:
        self.provider = provider
        self.max_retries = max_retries

    async def generate(self) -> ProfileLibrary:
        profiles = []
        for profile_id in PROFILE_IDS:
            profiles.append(await self._generate_profile(profile_id))
        return ProfileLibrary(
            generated_by=type(self.provider).__name__,
            profiles=profiles,
        )

    async def _generate_profile(self, profile_id: str) -> ProfileDefinition:
        prompt = build_single_profile_prompt(profile_id)
        error = ""
        for attempt in range(1, self.max_retries + 1):
            retry_note = "" if not error else f"\nPrevious response was invalid: {error}. Correct it completely."
            try:
                raw = await self.provider.generate(
                    prompt + retry_note,
                    system_prompt=PROFILE_BUILDER_SYSTEM_PROMPT,
                    max_tokens=1600,
                )
            except TypeError:
                # The legacy local provider does not yet expose max_tokens.
                raw = await self.provider.generate(prompt + retry_note, system_prompt=PROFILE_BUILDER_SYSTEM_PROMPT)
            try:
                payload = json.loads(self._extract_json(raw))
                profile = ProfileDefinition.model_validate(payload)
                if profile.profile_id != profile_id:
                    raise ValueError(f"expected profile_id {profile_id}, got {profile.profile_id}")
                return profile
            except (json.JSONDecodeError, ValueError) as exc:
                error = str(exc)
        raise ProfileGenerationError(
            f"Profile {profile_id} generation failed after {self.max_retries} attempts: {error}"
        )

    @staticmethod
    def _extract_json(raw: str) -> str:
        match = _FENCE.search(raw.strip())
        return match.group(1) if match else raw.strip()
