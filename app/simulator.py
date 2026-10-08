"""Pure deterministic calculation. No model, network or database dependency."""
from decimal import Decimal, ROUND_HALF_UP

from .schemas import SimulatorInput


def calculate(inputs: SimulatorInput) -> dict:
    values = {key: Decimal(str(value)) for key, value in inputs.model_dump().items()}
    missed = values["monthly_leads"] * values["missed_rate"]
    recovered = missed * values["recovery_rate"]
    appointments = recovered * values["booking_rate"]
    customers = appointments * values["close_rate"]
    revenue = customers * values["average_sale"]
    net = revenue - values["monthly_cost"]

    def rounded(value):
        return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    return {
        "assumptions": inputs.model_dump(),
        "results": {
            "missed_leads": rounded(missed),
            "recovered_leads": rounded(recovered),
            "booked_appointments": rounded(appointments),
            "new_customers": rounded(customers),
            "monthly_revenue": rounded(revenue),
            "annual_revenue": rounded(revenue * 12),
            "monthly_net": rounded(net),
            "roi_percent": rounded(net / values["monthly_cost"] * 100) if values["monthly_cost"] else None,
            "break_even_customers": rounded(values["monthly_cost"] / values["average_sale"])
            if values["average_sale"] else None,
        },
        "formulas": {
            "missed_leads": "monthly_leads × missed_rate",
            "recovered_leads": "missed_leads × recovery_rate",
            "booked_appointments": "recovered_leads × booking_rate",
            "new_customers": "booked_appointments × close_rate",
            "monthly_revenue": "new_customers × average_sale",
            "annual_revenue": "monthly_revenue × 12",
            "monthly_net": "monthly_revenue − monthly_cost",
            "roi_percent": "monthly_net ÷ monthly_cost × 100; undefined if cost is zero",
            "break_even_customers": "monthly_cost ÷ average_sale; undefined if average_sale is zero",
        },
        "limitations": "User assumptions, not a forecast. Fractional customers are expected values; annual excludes seasonality.",
    }
