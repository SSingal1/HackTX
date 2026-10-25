from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Money(DomainModel):
    amount: Decimal
    currency: str = Field(default="USD", min_length=3, max_length=3)


class Vehicle(DomainModel):
    vehicle_id: str
    vin: str | None = None
    year: int = Field(ge=1980, le=2100)
    make: str = "Toyota"
    model: str
    trim: str | None = None
    mileage: int = Field(ge=0)


class ContractType(StrEnum):
    LEASE = "lease"
    FINANCE = "finance"
    CASH = "cash"


class Contract(DomainModel):
    contract_id: str
    contract_type: ContractType
    start_date: date | None = None
    maturity_date: date | None = None
    monthly_payment: Money | None = None
    payoff_amount: Money | None = None
    residual_value: Money | None = None
    annual_mileage_allowance: int | None = Field(default=None, ge=0)


class MobilityPreference(DomainModel):
    monthly_budget: Money | None = None
    expected_annual_miles: int | None = Field(default=None, ge=0)
    preferred_body_styles: list[str] = Field(default_factory=list)
    needs_all_wheel_drive: bool = False
    open_to_electrified: bool = True
    priorities: list[str] = Field(default_factory=list)


class ServiceEvent(DomainModel):
    service_event_id: str
    service_date: date
    mileage: int = Field(ge=0)
    description: str
    cost: Money | None = None


class CustomerProfile(DomainModel):
    profile_id: str
    first_name: str | None = None
    postal_code: str | None = None
    vehicle: Vehicle
    contract: Contract | None = None
    preferences: MobilityPreference = Field(default_factory=MobilityPreference)
    service_history: list[ServiceEvent] = Field(default_factory=list)


class Evidence(DomainModel):
    title: str
    source: str
    url: str | None = None
    retrieved_at: datetime
    summary: str | None = None
    value: Decimal | None = None


class RecommendationRequest(DomainModel):
    profile_id: str
    as_of_date: date = Field(default_factory=date.today)
    refresh_market_data: bool = False


class RecommendationOption(DomainModel):
    option_id: str
    action: str
    rank: int = Field(ge=1)
    score: float = Field(ge=0, le=1)
    headline: str
    explanation: str
    estimated_monthly_cost: Money | None = None
    estimated_one_time_cost: Money | None = None
    assumptions: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class Recommendation(DomainModel):
    run_id: str
    profile_id: str
    generated_at: datetime
    recommended_action: str
    options: list[RecommendationOption]
    next_step: str
