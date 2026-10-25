from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from nextmove.api.dependencies import get_decision_service
from nextmove.decision.models import DecisionRequest, FinanceTerms, OptionInput
from nextmove.services.decision_service import DecisionService

router = APIRouter(prefix="/decisions", tags=["decisions"])


class FinanceTermsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    principal: Decimal = Field(ge=0)
    annual_rate: Decimal = Field(ge=0)
    term_months: int = Field(gt=0)

    def to_domain(self) -> FinanceTerms:
        return FinanceTerms(self.principal, self.annual_rate, self.term_months)


class OptionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    option_id: str
    label: str
    cash_due: Decimal = Field(ge=0)
    finance: FinanceTermsPayload | None = None
    monthly_payment: Decimal | None = Field(default=None, ge=0)
    recurring_monthly_cost: Decimal = Field(default=Decimal("0"), ge=0)
    one_time_costs: Decimal = Field(default=Decimal("0"), ge=0)
    estimated_ending_value: Decimal | None = Field(default=None, ge=0)
    remaining_debt_at_horizon: Decimal | None = Field(default=None, ge=0)
    hard_constraint_failures: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)

    def to_domain(self) -> OptionInput:
        return OptionInput(
            option_id=self.option_id,
            label=self.label,
            cash_due=self.cash_due,
            finance=self.finance.to_domain() if self.finance else None,
            monthly_payment=self.monthly_payment,
            recurring_monthly_cost=self.recurring_monthly_cost,
            one_time_costs=self.one_time_costs,
            estimated_ending_value=self.estimated_ending_value,
            remaining_debt_at_horizon=self.remaining_debt_at_horizon,
            hard_constraint_failures=tuple(self.hard_constraint_failures),
            evidence_ids=tuple(self.evidence_ids),
        )


class DecisionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: str
    run_id: str
    decision_type: str = "lease_end"
    horizon_months: int = Field(gt=0, le=120)
    options: list[OptionPayload] = Field(min_length=1)
    max_cash_due: Decimal | None = Field(default=None, ge=0)
    max_monthly_outflow: Decimal | None = Field(default=None, ge=0)
    assumptions: dict[str, Any] = Field(default_factory=dict)
    unknowns: list[str] = Field(default_factory=list)
    market_query: str
    location: str | None = None

    def to_domain(self) -> DecisionRequest:
        return DecisionRequest(
            profile_id=self.profile_id,
            run_id=self.run_id,
            decision_type=self.decision_type,
            horizon_months=self.horizon_months,
            options=tuple(option.to_domain() for option in self.options),
            max_cash_due=self.max_cash_due,
            max_monthly_outflow=self.max_monthly_outflow,
            assumptions=self.assumptions,
            unknowns=tuple(self.unknowns),
        )


@router.post("/evaluate", response_model=dict[str, Any])
def evaluate_decision(
    payload: DecisionPayload,
    service: DecisionService = Depends(get_decision_service),
) -> dict[str, Any]:
    try:
        result = service.decide(
            payload.to_domain(),
            market_query=payload.market_query,
            location=payload.location,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return result.to_api_dict()
