"""Synthetic Nessie-shaped banking for the hackathon affordability demo."""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def banking_forensics(profile: dict[str, Any]) -> dict[str, Any]:
    """Derive FCF and liquidity signals from explicitly synthetic banking records."""
    raw = profile.get("banking") or {}
    accounts = raw.get("accounts") or []
    deposits = raw.get("deposits") or []
    bills = raw.get("bills") or []
    purchases = raw.get("essential_spending") or []
    loans = raw.get("loans") or []

    liquidity = sum(Decimal(str(item.get("balance") or 0)) for item in accounts)
    monthly_income = sum(Decimal(str(item.get("monthly_amount") or 0)) for item in deposits)
    recurring_bills = sum(Decimal(str(item.get("monthly_amount") or 0)) for item in bills)
    essentials = sum(Decimal(str(item.get("monthly_amount") or 0)) for item in purchases)
    loan_payments = sum(Decimal(str(item.get("monthly_payment") or 0)) for item in loans)
    emergency_factor = Decimal(str(raw.get("emergency_floor_factor") or 1))
    cash_to_protect = recurring_bills + loan_payments + emergency_factor * essentials
    free_cash_flow = monthly_income - recurring_bills - essentials - loan_payments
    safe_to_spend = max(Decimal(0), liquidity - cash_to_protect)
    dti = loan_payments / monthly_income if monthly_income else Decimal(0)

    return {
        "source": "synthetic_nessie_fixture",
        "simulated": True,
        "accounts": accounts,
        "income_streams": deposits,
        "upcoming_bills": bills,
        "loan_obligations": loans,
        "monthly_income": float(monthly_income),
        "recurring_bills": float(recurring_bills),
        "living_essentials": float(essentials),
        "loan_payments": float(loan_payments),
        "total_liquidity": float(liquidity),
        "cash_to_protect": float(cash_to_protect),
        "safe_to_spend": float(safe_to_spend),
        "monthly_free_cash_flow": float(free_cash_flow),
        "current_dti": float(dti),
        "emergency_floor_factor": float(emergency_factor),
        "formula": (
            "Cash to Protect = upcoming recurring bills + minimum loan payments + "
            "emergency factor x monthly essentials"
        ),
    }


def synthetic_finance_plan(
    vehicle: dict[str, Any], banking: dict[str, Any], *, mode: str
) -> dict[str, Any]:
    """Build a disclosed what-if plan; this never creates a loan or offer."""
    if mode == "lease":
        cash_due = Decimal(str(vehicle["lease_due"]))
        payment = Decimal(str(vehicle["lease_monthly"]))
        term = 36
        apr = None
        trade_credit = Decimal(0)
    else:
        msrp = Decimal(str(vehicle["msrp"]))
        trade_credit = Decimal(str(vehicle.get("trade_credit") or 0))
        safe_to_spend = Decimal(str(banking["safe_to_spend"]))
        cash_due = min(Decimal(1500), max(Decimal(500), safe_to_spend * Decimal("0.12")))
        apr = Decimal(str(vehicle.get("planning_apr") or 5.9))
        term = 72
        principal = max(Decimal(0), msrp - trade_credit - cash_due)
        monthly_rate = apr / Decimal(1200)
        payment = (
            principal / term
            if monthly_rate == 0
            else principal
            * monthly_rate
            * (1 + monthly_rate) ** term
            / ((1 + monthly_rate) ** term - 1)
        )

    income = Decimal(str(banking["monthly_income"]))
    existing_debt = Decimal(str(banking["loan_payments"]))
    post_upgrade_fcf = Decimal(str(banking["monthly_free_cash_flow"])) - payment
    post_upgrade_dti = (existing_debt + payment) / income if income else Decimal(0)
    risk = "safe" if post_upgrade_fcf >= income * Decimal("0.20") else "caution"
    if post_upgrade_fcf < 0:
        risk = "high_risk"
    return {
        "name": "Liquidity-preserving plan" if mode == "purchase" else "Published lease fixture",
        "mode": mode,
        "cash_due": float(cash_due.quantize(Decimal(".01"))),
        "monthly_payment": float(payment.quantize(Decimal(".01"))),
        "term_months": term,
        "apr": float(apr) if apr is not None else None,
        "trade_credit": float(trade_credit),
        "post_upgrade_fcf": float(post_upgrade_fcf.quantize(Decimal(".01"))),
        "post_upgrade_dti": float(post_upgrade_dti.quantize(Decimal(".0001"))),
        "risk": risk,
        "simulated": True,
        "notice": (
            "Synthetic what-if plan using profile cash flow and an illustrative trade credit. "
            "It is not an application, approval, quote, or offer. Taxes and fees are excluded."
        ),
    }
