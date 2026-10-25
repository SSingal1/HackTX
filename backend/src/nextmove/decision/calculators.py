from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def monthly_loan_payment(principal: Decimal, annual_rate: Decimal, term_months: int) -> Decimal:
    if principal < 0 or annual_rate < 0:
        raise ValueError("principal and annual_rate cannot be negative")
    if term_months <= 0:
        raise ValueError("term_months must be positive")
    if principal == 0:
        return Decimal("0.00")
    if annual_rate == 0:
        return money(principal / term_months)
    rate = annual_rate / Decimal("12")
    factor = (Decimal("1") + rate) ** term_months
    return money(principal * rate * factor / (factor - Decimal("1")))


def remaining_loan_balance(
    principal: Decimal, annual_rate: Decimal, term_months: int, payments_made: int
) -> Decimal:
    if not 0 <= payments_made <= term_months:
        raise ValueError("payments_made must be between zero and term_months")
    if payments_made == term_months:
        return Decimal("0.00")
    payment = monthly_loan_payment(principal, annual_rate, term_months)
    if annual_rate == 0:
        return money(max(Decimal("0"), principal - payment * payments_made))
    rate = annual_rate / Decimal("12")
    factor = (Decimal("1") + rate) ** payments_made
    return money(max(Decimal("0"), principal * factor - payment * (factor - Decimal("1")) / rate))


def projected_excess_mileage(
    current_mileage: int, allowance: int, months_remaining: int, expected_monthly_miles: int
) -> int:
    if any(v < 0 for v in (current_mileage, allowance, months_remaining, expected_monthly_miles)):
        raise ValueError("mileage inputs cannot be negative")
    return max(0, current_mileage + months_remaining * expected_monthly_miles - allowance)


def excess_mileage_charge(excess_miles: int, rate_per_mile: Decimal) -> Decimal:
    if excess_miles < 0 or rate_per_mile < 0:
        raise ValueError("excess miles and rate cannot be negative")
    return money(Decimal(excess_miles) * rate_per_mile)


def estimated_equity(offer_value: Decimal | None, payoff: Decimal | None) -> Decimal | None:
    return None if offer_value is None or payoff is None else money(offer_value - payoff)
