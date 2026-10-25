from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from enum import Enum, StrEnum
from typing import Any


class EvidenceStatus(StrEnum):
    VERIFIED = "verified"
    NEEDS_VERIFICATION = "needs_verification"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    title: str
    url: str
    retrieved_at: str
    source: str = "serpapi"
    status: EvidenceStatus = EvidenceStatus.NEEDS_VERIFICATION
    fact: str | None = None


@dataclass(frozen=True)
class FinanceTerms:
    principal: Decimal
    annual_rate: Decimal
    term_months: int


@dataclass(frozen=True)
class OptionInput:
    option_id: str
    label: str
    cash_due: Decimal
    finance: FinanceTerms | None = None
    monthly_payment: Decimal | None = None
    recurring_monthly_cost: Decimal = Decimal("0")
    one_time_costs: Decimal = Decimal("0")
    estimated_ending_value: Decimal | None = None
    remaining_debt_at_horizon: Decimal | None = None
    hard_constraint_failures: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class DecisionRequest:
    profile_id: str
    run_id: str
    decision_type: str
    horizon_months: int
    options: tuple[OptionInput, ...]
    max_cash_due: Decimal | None = None
    max_monthly_outflow: Decimal | None = None
    assumptions: dict[str, Any] = field(default_factory=dict)
    unknowns: tuple[str, ...] = ()


@dataclass(frozen=True)
class OptionResult:
    option_id: str
    label: str
    cash_due: Decimal
    monthly_payment: Decimal
    monthly_operating_cost: Decimal
    total_cash_outflow: Decimal
    estimated_ending_equity: Decimal | None
    economic_cost: Decimal | None
    feasible: bool
    feasibility_reasons: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    rank: int | None = None


@dataclass(frozen=True)
class DecisionResult:
    profile_id: str
    run_id: str
    decision_type: str
    horizon_months: int
    options: tuple[OptionResult, ...]
    assumptions: dict[str, Any]
    unknowns: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    next_action: str
    comparison_basis: str
    explanation: str | None = None

    def to_api_dict(self) -> dict[str, Any]:
        def convert(value: Any) -> Any:
            if isinstance(value, Decimal):
                return float(value)
            if isinstance(value, Enum):
                return value.value
            if isinstance(value, dict):
                return {k: convert(v) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [convert(v) for v in value]
            return value

        return convert(asdict(self))
