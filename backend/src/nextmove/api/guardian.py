"""Synthetic Guardian journey; no real account access or provider contact."""

import json
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from nextmove.api.dependencies import (
    get_guardian_chat_service,
    get_guardian_market_service,
    get_guardian_provider_service,
    get_guardian_repository,
)
from nextmove.data.guardian import GuardianProfileRepository
from nextmove.decision.engine import DecisionEngine
from nextmove.decision.models import DecisionRequest, OptionInput
from nextmove.services.guardian_chat import GuardianChatService
from nextmove.services.guardian_market import GuardianMarketEvidenceService
from nextmove.services.guardian_providers import GuardianProviderService
from nextmove.settings import get_settings

router = APIRouter(prefix="/guardian", tags=["synthetic-guardian"])
UPGRADE_OPTIONS = {
    "corolla_hybrid": {
        "label": "2025 Corolla Hybrid LE",
        "cash_due": 3000,
        "purchase_monthly": 440,
        "lease_monthly": 329,
        "lease_due": 2999,
        "mpg": 50,
        "routine": 300,
        "msrp": 24760,
    },
    "camry_le": {
        "label": "2025 Camry LE",
        "cash_due": 3500,
        "purchase_monthly": 510,
        "lease_monthly": 389,
        "lease_due": 3999,
        "mpg": 51,
        "routine": 300,
        "msrp": 28400,
    },
    "prius_le": {
        "label": "2025 Prius LE",
        "cash_due": 3500,
        "purchase_monthly": 520,
        "lease_monthly": 399,
        "lease_due": 3999,
        "mpg": 57,
        "routine": 300,
        "msrp": 28350,
    },
}


class ComparePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile: str = "alex"
    miles: int = Field(default=12000, ge=6000, le=30000)
    repair: Decimal = Field(default=Decimal("1800"), ge=0, le=4500)
    reserve: Decimal = Field(default=Decimal("2000"), ge=500, le=6000)
    discount: bool = False
    # This is never inferred from web search.  It may only be supplied after the
    # client has shown the user an attributable public-source reference.
    fuel_price_per_gallon: Decimal = Field(default=Decimal("3.50"), ge=1, le=10)
    cash_on_hand: Decimal | None = Field(default=None, ge=0, le=100000)
    monthly_free_cash_flow: Decimal | None = Field(default=None, ge=0, le=50000)
    upgrade_id: str = Field(
        default="corolla_hybrid", pattern="^(corolla_hybrid|camry_le|prius_le)$"
    )
    upgrade_mode: str = Field(default="purchase", pattern="^(purchase|lease)$")


class InquiryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inputs: ComparePayload
    consent: bool
    request_id: str = Field(min_length=1, max_length=100)


class ChatHistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=500)


class ChatPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile: str = Field(min_length=1, max_length=80)
    scenario: ComparePayload
    view: str = Field(min_length=1, max_length=40, pattern=r"^[a-zA-Z0-9_-]+$")
    message: str = Field(min_length=1, max_length=1000)
    history: list[ChatHistoryItem] = Field(default_factory=list, max_length=6)
    user_context: dict[str, str | float | list[str] | None] = Field(default_factory=dict)


class AdoptFuelReferencePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile: str = Field(min_length=1, max_length=80)
    evidence_id: str = Field(min_length=1, max_length=160)


def selected(repository: GuardianProfileRepository, profile_id: str) -> dict:
    profile = repository.get_guardian_profile(profile_id)
    if profile is None:
        raise HTTPException(404, "Synthetic Guardian profile not found")
    return profile


@router.get("/profiles")
def profiles(repository: GuardianProfileRepository = Depends(get_guardian_repository)) -> dict:
    loaded = repository.list_guardian_profiles()
    sources = sorted({profile["source"]["type"] for profile in loaded.values()})
    return {"profiles": loaded, "simulated": True, "sources": sources}


@router.get("/integration-status")
def integration_status() -> dict:
    """Safe, non-secret runtime diagnostics for the hackathon demo UI."""
    settings = get_settings()
    return {
        "gemini": {
            "configured": bool(settings.gemini_api_key),
            "model": settings.guardian_gemini_model or settings.gemini_model,
            "timeout_seconds": settings.guardian_gemini_timeout_seconds,
        },
        "serpapi": {
            "configured": bool(settings.serpapi_api_key),
            "provider_cache_seconds": settings.guardian_provider_cache_ttl_seconds,
            "market_cache_seconds": settings.guardian_market_cache_ttl_seconds,
            "market_refresh_searches": 5,
        },
        "snowflake": {
            "configured": bool(settings.snowflake_account and settings.snowflake_user),
            "database": settings.snowflake_database,
            "schema": settings.snowflake_schema,
        },
    }


@router.get("/providers")
def providers(
    profile: str,
    refresh: bool = False,
    service: GuardianProviderService = Depends(get_guardian_provider_service),
) -> dict:
    result = service.discover(profile, refresh=refresh)
    if result is None:
        raise HTTPException(404, "Synthetic Guardian profile not found")
    return result


@router.get("/market-evidence")
def market_evidence(
    profile: str,
    refresh: bool = False,
    service: GuardianMarketEvidenceService = Depends(get_guardian_market_service),
) -> dict:
    """Refresh is the sole path that spends SerpApi quota for this evidence."""
    result = service.evidence(profile, refresh=refresh)
    if result is None:
        raise HTTPException(404, "Synthetic Guardian profile not found")
    return result


@router.post("/market-evidence/adopt-fuel")
def adopt_fuel_reference(
    payload: AdoptFuelReferencePayload,
    service: GuardianMarketEvidenceService = Depends(get_guardian_market_service),
) -> dict:
    """Prepare a confirmed fuel input without changing a profile or comparison."""
    try:
        result = service.adopt_fuel_reference(payload.profile, payload.evidence_id)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    if result is None:
        raise HTTPException(404, "Synthetic Guardian profile not found")
    return result


@router.post("/compare")
def compare(
    payload: ComparePayload,
    repository: GuardianProfileRepository = Depends(get_guardian_repository),
) -> dict:
    return _compare(payload, repository)


@router.post("/chat")
def chat(
    payload: ChatPayload,
    repository: GuardianProfileRepository = Depends(get_guardian_repository),
    service: GuardianChatService = Depends(get_guardian_chat_service),
) -> dict:
    if payload.scenario.profile != payload.profile:
        raise HTTPException(422, "Scenario profile must match selected profile")
    comparison = _compare(payload.scenario, repository)
    result = service.respond(
        profile_id=payload.profile,
        scenario=payload.scenario.model_dump(mode="json"),
        comparison=comparison,
        view=payload.view,
        message=payload.message,
        history=[item.model_dump() for item in payload.history],
        user_context=payload.user_context,
    )
    if result is None:
        raise HTTPException(404, "Synthetic Guardian profile not found")
    return {
        "message": result.message,
        "cited_evidence_ids": result.cited_evidence_ids,
        "scenario_change": result.scenario_change,
        "fallback": result.fallback,
        "warning": result.warning,
        "simulated": True,
    }


def _compare(payload: ComparePayload, repository: GuardianProfileRepository) -> dict:
    p = selected(repository, payload.profile)
    upgrade = UPGRADE_OPTIONS[payload.upgrade_id]
    coverage = min(Decimal(p["coverage"]), payload.repair)
    discount = min(Decimal(50), payload.repair) if payload.discount and not coverage else Decimal(0)
    oop = payload.repair - coverage - discount
    fuel_price = Decimal(payload.fuel_price_per_gallon)
    fuel_keep = (Decimal(payload.miles) / 30 * fuel_price).quantize(Decimal(".01"))
    fuel_replace = (Decimal(payload.miles) / Decimal(upgrade["mpg"]) * fuel_price).quantize(
        Decimal(".01")
    )
    replacement_cash_due = Decimal(
        str(upgrade["lease_due"] if payload.upgrade_mode == "lease" else upgrade["cash_due"])
    )
    replacement_payment = Decimal(
        str(
            upgrade["lease_monthly"]
            if payload.upgrade_mode == "lease"
            else upgrade["purchase_monthly"]
        )
    )
    starting_cash = payload.cash_on_hand if payload.cash_on_hand is not None else Decimal(p["cash"])
    keep_cash, replace_cash = starting_cash - oop, starting_cash - replacement_cash_due
    keep_reserve_ok, replace_reserve_ok = (
        keep_cash >= payload.reserve,
        replace_cash >= payload.reserve,
    )
    keep_monthly = (
        Decimal(p.get("contract", {}).get("monthly_payment") or 0) * 12 + Decimal(600) + fuel_keep
    ) / 12
    replace_monthly = (replacement_payment * 12 + Decimal(upgrade["routine"]) + fuel_replace) / 12
    monthly_flow = payload.monthly_free_cash_flow
    keep_monthly_ok = monthly_flow is None or keep_monthly <= monthly_flow
    replace_monthly_ok = monthly_flow is None or replace_monthly <= monthly_flow
    keep_ok, replace_ok = (
        keep_reserve_ok and keep_monthly_ok,
        replace_reserve_ok and replace_monthly_ok,
    )
    result = (
        DecisionEngine()
        .evaluate(
            DecisionRequest(
                profile_id=payload.profile,
                run_id=str(uuid4()),
                decision_type="service_guardian",
                horizon_months=12,
                options=(
                    OptionInput(
                        "keep",
                        "Keep and service Camry",
                        oop,
                        one_time_costs=Decimal(600) + fuel_keep,
                        monthly_payment=Decimal(
                            str(p.get("contract", {}).get("monthly_payment") or 0)
                        ),
                        hard_constraint_failures=tuple(
                            reason
                            for condition, reason in (
                                (keep_reserve_ok, "Remaining cash is below the protected floor"),
                                (
                                    keep_monthly_ok,
                                    "Ongoing monthly cost exceeds self-reported free cash flow",
                                ),
                            )
                            if not condition
                        ),
                    ),
                    OptionInput(
                        "replace",
                        f"Explore {upgrade['label']} ({payload.upgrade_mode})",
                        replacement_cash_due,
                        monthly_payment=replacement_payment,
                        one_time_costs=Decimal(upgrade["routine"]) + fuel_replace,
                        hard_constraint_failures=tuple(
                            reason
                            for condition, reason in (
                                (replace_reserve_ok, "Remaining cash is below the protected floor"),
                                (
                                    replace_monthly_ok,
                                    "Ongoing monthly cost exceeds self-reported free cash flow",
                                ),
                            )
                            if not condition
                        ),
                    ),
                ),
                assumptions={
                    "fuel_price": float(fuel_price),
                    "keep_mpg": 30,
                    "replacement_mpg": upgrade["mpg"],
                    "replacement_vehicle": upgrade["label"],
                    "replacement_mode": payload.upgrade_mode,
                    "replacement_msrp_reference": upgrade["msrp"],
                    "insurance_registration": "assumed equal",
                    "simulated": True,
                    "reserve_scope": "Protected cash floor after one-time cash due",
                    "cash_on_hand": float(starting_cash),
                    "monthly_free_cash_flow": float(monthly_flow)
                    if monthly_flow is not None
                    else None,
                },
                unknowns=(
                    "Ending vehicle values and equity are unknown.",
                    "Provider scope, coverage and financing require verification.",
                ),
            )
        )
        .to_api_dict()
    )
    keep, replacement = (Decimal(str(x["total_cash_outflow"])) for x in result["options"])
    difference = replacement - keep
    if not keep_ok and not replace_ok:
        title = "Let’s verify costs before choosing a path."
        text = (
            "Both paths leave less than your protected reserve. "
            "No affordable winner is established."
        )
    elif not keep_ok:
        title = "The repair needs a closer affordability check."
        text = "The repair leaves less than your reserve. Verify costs before committing."
    elif difference >= 0:
        title = "Keeping your Camry looks better for near-term cash flow."
        text = (
            f"Servicing uses ${difference:,.0f} less cash over 12 months. "
            f"The ${oop:,.0f} repair leaves ${keep_cash:,.0f} available. "
            "This is a cash-flow comparison, not total economic savings."
        )
    elif not replace_ok:
        title = "The upgrade needs an affordability check."
        text = "The upgrade has lower cash outflow but would breach your upfront reserve."
    else:
        title = "Compare the replacement quote more closely."
        text = (
            f"The replacement uses ${-difference:,.0f} less cash in this scenario. "
            "Verify financing and ending equity before choosing."
        )
    numbers = dict(
        coverage=coverage,
        discount=discount,
        oop=oop,
        fuelKeep=fuel_keep,
        fuelReplace=fuel_replace,
        keep=keep,
        replace=replacement,
        difference=difference,
        keepCash=keep_cash,
        replaceCash=replace_cash,
        startingCash=starting_cash,
        fuelPrice=fuel_price,
        keepMonthly=keep_monthly,
        replaceMonthly=replace_monthly,
        replacementCashDue=replacement_cash_due,
        replacementPayment=replacement_payment,
    )
    return {
        "calculation": {
            **{k: float(v) for k, v in numbers.items()},
            "keepOK": keep_ok,
            "replaceOK": replace_ok,
            "keepReserveOK": keep_reserve_ok,
            "replaceReserveOK": replace_reserve_ok,
            "keepMonthlyOK": keep_monthly_ok,
            "replaceMonthlyOK": replace_monthly_ok,
        },
        "recommendation": {
            "title": title,
            "text": text,
            "warning": not keep_ok or (difference < 0 and not replace_ok),
        },
        "decision": result,
        "profile": p,
        "upgrade_options": UPGRADE_OPTIONS,
        "selected_upgrade": {"id": payload.upgrade_id, "mode": payload.upgrade_mode, **upgrade},
        "source": p["source"],
        "simulated": True,
    }


def database() -> sqlite3.Connection:
    path = Path(get_settings().guardian_database_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS guardian_inquiries "
        "(request_id TEXT PRIMARY KEY, profile TEXT NOT NULL, body TEXT NOT NULL)"
    )
    return connection


@router.get("/history")
def history(
    profile: str,
    repository: GuardianProfileRepository = Depends(get_guardian_repository),
) -> dict:
    selected(repository, profile)
    with database() as connection:
        rows = connection.execute(
            "SELECT body FROM guardian_inquiries WHERE profile=? ORDER BY rowid DESC LIMIT 20",
            (profile,),
        ).fetchall()
    return {"inquiries": [json.loads(row[0]) for row in rows], "simulated": True}


@router.post("/inquiries")
def save_inquiry(
    payload: InquiryPayload,
    repository: GuardianProfileRepository = Depends(get_guardian_repository),
) -> dict:
    if not payload.consent:
        raise HTTPException(422, "Confirm the simulated inquiry notice before saving")
    result = _compare(payload.inputs, repository)
    entry = dict(
        id=payload.request_id,
        name=selected(repository, payload.inputs.profile)["name"],
        createdAt=datetime.now(UTC).isoformat(),
        cost=result["calculation"]["oop"],
        profile=payload.inputs.profile,
        inputs=payload.inputs.model_dump(mode="json"),
        results=result["calculation"],
        decision=result["decision"],
        action="verify-service-estimate",
        simulated=True,
    )
    with database() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO guardian_inquiries VALUES (?, ?, ?)",
            (payload.request_id, payload.inputs.profile, json.dumps(entry)),
        )
        row = connection.execute(
            "SELECT profile, body FROM guardian_inquiries WHERE request_id=?", (payload.request_id,)
        ).fetchone()
    if row[0] != payload.inputs.profile:
        raise HTTPException(409, "Request ID already used for another profile")
    return json.loads(row[1])
