import unittest
from decimal import Decimal

from nextmove.decision.calculators import (
    excess_mileage_charge,
    monthly_loan_payment,
    projected_excess_mileage,
)
from nextmove.decision.engine import DecisionEngine
from nextmove.decision.models import DecisionRequest, FinanceTerms, OptionInput


class CalculatorTests(unittest.TestCase):
    def test_demo_mileage_fixtures_reconcile(self):
        miles = projected_excess_mileage(33000, 36000, 4, 1200)
        self.assertEqual(
            (miles, excess_mileage_charge(miles, Decimal(".25"))), (1800, Decimal("450.00"))
        )
        self.assertEqual(
            excess_mileage_charge(projected_excess_mileage(33000, 36000, 4, 2000), Decimal(".25")),
            Decimal("1250.00"),
        )

    def test_zero_apr_branch(self):
        self.assertEqual(
            monthly_loan_payment(Decimal("12000"), Decimal("0"), 24), Decimal("500.00")
        )


class EngineTests(unittest.TestCase):
    def test_missing_ending_values_withholds_economic_winner(self):
        r = DecisionEngine().evaluate(
            DecisionRequest(
                "p",
                "r",
                "lease_end",
                12,
                (
                    OptionInput("a", "Keep", Decimal("0"), monthly_payment=Decimal("400")),
                    OptionInput("b", "Replace", Decimal("2000"), monthly_payment=Decimal("300")),
                ),
            )
        )
        self.assertEqual(r.comparison_basis, "cash_flow")
        self.assertTrue(all(o.economic_cost is None for o in r.options))

    def test_budget_failure_excludes_option_from_rank(self):
        req = DecisionRequest(
            "p",
            "r",
            "lease_end",
            12,
            (
                OptionInput(
                    "a",
                    "Affordable",
                    Decimal("500"),
                    finance=FinanceTerms(Decimal("12000"), Decimal("0"), 24),
                    estimated_ending_value=Decimal("9000"),
                ),
                OptionInput(
                    "b",
                    "Too much cash",
                    Decimal("2500"),
                    monthly_payment=Decimal("100"),
                    estimated_ending_value=Decimal("5000"),
                    remaining_debt_at_horizon=Decimal("0"),
                ),
            ),
            max_cash_due=Decimal("1000"),
            max_monthly_outflow=Decimal("500"),
        )
        by = {o.option_id: o for o in DecisionEngine().evaluate(req).options}
        self.assertEqual(by["a"].rank, 1)
        self.assertIsNone(by["b"].rank)
