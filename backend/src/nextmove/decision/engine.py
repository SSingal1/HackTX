from dataclasses import replace
from decimal import Decimal

from .calculators import money, monthly_loan_payment, remaining_loan_balance
from .models import DecisionRequest, DecisionResult, OptionInput, OptionResult


class DecisionEngine:
    """Computes comparable options without using a language model."""

    def evaluate(self, request: DecisionRequest) -> DecisionResult:
        if request.horizon_months <= 0:
            raise ValueError("horizon_months must be positive")
        if not request.options:
            raise ValueError("at least one option is required")
        results = tuple(self._evaluate_option(o, request) for o in request.options)
        basis = (
            "economic_cost"
            if all(r.estimated_ending_equity is not None for r in results)
            else "cash_flow"
        )
        feasible = [r for r in results if r.feasible]
        ordered = sorted(
            feasible,
            key=(lambda r: (r.economic_cost, r.total_cash_outflow))
            if basis == "economic_cost"
            else (lambda r: r.total_cash_outflow),
        )
        ranks = {r.option_id: i + 1 for i, r in enumerate(ordered)}
        ranked = tuple(replace(r, rank=ranks.get(r.option_id)) for r in results)
        action = (
            f"Review and verify the assumptions for {ordered[0].label}."
            if ordered
            else "Adjust the budget or request verified terms before choosing an option."
        )
        evidence_ids = tuple(dict.fromkeys(e for r in ranked for e in r.evidence_ids))
        return DecisionResult(
            request.profile_id,
            request.run_id,
            request.decision_type,
            request.horizon_months,
            ranked,
            request.assumptions,
            request.unknowns,
            evidence_ids,
            action,
            basis,
        )

    def _evaluate_option(self, option: OptionInput, request: DecisionRequest) -> OptionResult:
        payment, debt = option.monthly_payment, option.remaining_debt_at_horizon
        if option.finance:
            f = option.finance
            payment = monthly_loan_payment(f.principal, f.annual_rate, f.term_months)
            debt = remaining_loan_balance(
                f.principal,
                f.annual_rate,
                f.term_months,
                min(request.horizon_months, f.term_months),
            )
        payment = payment or Decimal("0")
        months_paid = (
            min(request.horizon_months, option.finance.term_months)
            if option.finance
            else request.horizon_months
        )
        monthly_outflow = payment + option.recurring_monthly_cost
        total = money(
            option.cash_due
            + option.one_time_costs
            + payment * months_paid
            + option.recurring_monthly_cost * request.horizon_months
        )
        equity = (
            money(option.estimated_ending_value - debt)
            if option.estimated_ending_value is not None and debt is not None
            else None
        )
        reasons = list(option.hard_constraint_failures)
        if request.max_cash_due is not None and option.cash_due > request.max_cash_due:
            reasons.append("cash due exceeds available reserve")
        if (
            request.max_monthly_outflow is not None
            and monthly_outflow > request.max_monthly_outflow
        ):
            reasons.append("monthly outflow exceeds budget")
        return OptionResult(
            option.option_id,
            option.label,
            money(option.cash_due),
            money(payment),
            money(option.recurring_monthly_cost),
            total,
            equity,
            money(total - equity) if equity is not None else None,
            not reasons,
            tuple(reasons),
            option.evidence_ids,
        )
