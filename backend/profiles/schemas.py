"""Strict data contracts for the AI-authored simulation profile library."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PROFILE_IDS = (
    "REGULAR_CUSTOMER",
    "GIFT_CARD_FRAUD",
    "CARD_TESTING",
    "ACCOUNT_TAKEOVER",
    "CREDENTIAL_STUFFING",
    "REFUND_FRAUD",
    "SYNTHETIC_IDENTITY_FRAUD",
    "MONEY_MULE_TRANSFER",
    "AUTHORIZED_PUSH_PAYMENT_SCAM",
    "VPN_HIGH_RISK_TRAVELER",
)
ProfileId = Literal[
    "REGULAR_CUSTOMER", "GIFT_CARD_FRAUD", "CARD_TESTING", "ACCOUNT_TAKEOVER",
    "CREDENTIAL_STUFFING", "REFUND_FRAUD", "SYNTHETIC_IDENTITY_FRAUD",
    "MONEY_MULE_TRANSFER", "AUTHORIZED_PUSH_PAYMENT_SCAM", "VPN_HIGH_RISK_TRAVELER",
]


class RiskTendency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StrictProfileModel(BaseModel):
    """Reject invented keys rather than silently accepting LLM hallucinations."""

    model_config = ConfigDict(extra="forbid")


class FloatRange(StrictProfileModel):
    minimum: float
    maximum: float

    @model_validator(mode="after")
    def ordered(self) -> "FloatRange":
        if self.minimum > self.maximum:
            raise ValueError("minimum must not exceed maximum")
        return self


class UnitFloatRange(FloatRange):
    minimum: float = Field(ge=0, le=1)
    maximum: float = Field(ge=0, le=1)


class IntRange(StrictProfileModel):
    minimum: int = Field(ge=0)
    maximum: int = Field(ge=0)

    @model_validator(mode="after")
    def ordered(self) -> "IntRange":
        if self.minimum > self.maximum:
            raise ValueError("minimum must not exceed maximum")
        return self


class IdentityAttributes(StrictProfileModel):
    age_years: IntRange
    occupations: list[str] = Field(min_length=1, max_length=5)
    monthly_income_usd: FloatRange
    device_types: list[str] = Field(min_length=1, max_length=4)
    browsers: list[str] = Field(min_length=1, max_length=4)
    preferred_payment_methods: list[str] = Field(min_length=1, max_length=4)
    typical_login_hour_utc: IntRange

    @field_validator("typical_login_hour_utc")
    @classmethod
    def valid_login_hours(cls, value: IntRange) -> IntRange:
        if value.maximum > 23:
            raise ValueError("typical_login_hour_utc must be between 0 and 23")
        return value


class BehavioralTelemetryProfile(StrictProfileModel):
    typing_speed_cpm: IntRange
    typing_error_rate: UnitFloatRange
    mouse_movement_quality: UnitFloatRange
    scroll_behavior: UnitFloatRange
    device_reputation: UnitFloatRange
    ip_reputation: UnitFloatRange
    vpn_probability: UnitFloatRange
    tor_probability: UnitFloatRange
    automation_probability: UnitFloatRange


class TransactionalProfile(StrictProfileModel):
    transaction_frequency_per_day: IntRange
    average_transaction_amount_usd: FloatRange
    transaction_amount_usd: FloatRange
    account_age_days: IntRange
    previous_transactions: IntRange
    merchant_categories: list[str] = Field(min_length=1, max_length=6)
    known_device_probability: UnitFloatRange
    unfamiliar_recipient_probability: UnitFloatRange
    password_changed_recently_probability: UnitFloatRange
    refund_attempts: IntRange
    counterparties_per_day: IntRange


class ProfileDefinition(StrictProfileModel):
    profile_id: ProfileId
    display_name: str = Field(min_length=3, max_length=80)
    domain: str = Field(min_length=3, max_length=80)
    description: str = Field(min_length=20, max_length=500)
    risk_tendency: RiskTendency
    identity: IdentityAttributes
    behavioral: BehavioralTelemetryProfile
    transactional: TransactionalProfile


class ProfileLibrary(StrictProfileModel):
    schema_version: Literal["1.0"] = "1.0"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    generated_by: str = Field(min_length=3, max_length=120)
    profiles: list[ProfileDefinition] = Field(min_length=10, max_length=10)

    @model_validator(mode="after")
    def exact_profile_set(self) -> "ProfileLibrary":
        ids = [profile.profile_id for profile in self.profiles]
        if len(set(ids)) != 10 or set(ids) != set(PROFILE_IDS):
            raise ValueError("profiles must contain each of the required 10 profile IDs exactly once")
        return self
