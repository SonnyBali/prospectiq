import pytest
from pydantic import ValidationError

from app.schemas import SimulatorInput
from app.simulator import calculate


def test_revenue_is_expected_value_not_rounded_customer_count():
    result = calculate(SimulatorInput(monthly_leads=100, missed_rate=.1, recovery_rate=.5, booking_rate=.5, close_rate=.5, average_sale=100, monthly_cost=50))
    assert result["results"]["new_customers"] == 1.25
    assert result["results"]["monthly_revenue"] == 125
    assert result["results"]["annual_revenue"] == 1500
    assert result["results"]["monthly_net"] == 75
    assert result["results"]["roi_percent"] == 150


def test_no_leads_keeps_cost_and_negative_net():
    result = calculate(SimulatorInput(monthly_leads=0, monthly_cost=497))
    assert result["results"]["monthly_revenue"] == 0
    assert result["results"]["monthly_net"] == -497
    assert result["results"]["roi_percent"] == -100


def test_zero_denominators_are_undefined_not_infinity():
    result = calculate(SimulatorInput(monthly_cost=0, average_sale=0))
    assert result["results"]["roi_percent"] is None
    assert result["results"]["break_even_customers"] is None


@pytest.mark.parametrize("field,value", [("missed_rate", 1.1), ("close_rate", -1), ("average_sale", float("nan")), ("monthly_cost", float("inf")), ("monthly_leads", 1.5)])
def test_rejects_invalid_assumptions(field, value):
    with pytest.raises(ValidationError):
        SimulatorInput(**{field: value})


def test_decimal_money_rounding_is_consistent():
    result = calculate(SimulatorInput(monthly_leads=1, missed_rate=1, recovery_rate=1, booking_rate=1, close_rate=1, average_sale=1.005, monthly_cost=0))
    assert result["results"]["monthly_revenue"] == 1.01
    assert result["results"]["annual_revenue"] == 12.06
