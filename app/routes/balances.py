from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.balances import (
    compute_net_balances,
    convert_balances_to_currency,
    get_settled_by_map,
    simplify_debts,
    simplify_debts_in_currency,
)
from app.database import get_db
from app.deps import get_trip_by_token
from app.exchange import get_rates_for_currencies
from app.serializers import serialize_expense, serialize_settlement, serialize_member

router = APIRouter()


def _to_plain_expense(expense_dict: dict) -> dict:
    """Ensure serialized expense dict has the shape balance functions expect."""
    return expense_dict


def _to_plain_settlement(settlement_dict: dict) -> dict:
    """Ensure serialized settlement dict has the shape balance functions expect."""
    return settlement_dict


@router.get("/trips/{access_token}/balances")
def get_balances(access_token: str, db: Session = Depends(get_db)):
    trip = get_trip_by_token(access_token, db)

    # Serialize ORM objects to plain dicts (string IDs, camelCase keys)
    members = [serialize_member(m) for m in trip.members]
    expenses = [serialize_expense(e) for e in trip.expenses]
    settlements = [serialize_settlement(s) for s in trip.settlements]

    trip_currency = trip.currency

    # Compute net balances
    net_balances = compute_net_balances(expenses, settlements, trip_currency)
    settled_by = get_settled_by_map(members)

    # Determine if consolidated mode
    is_consolidated = bool(trip.settlement_currency)
    consolidated_balances = None
    exchange_rates_response = None

    # Collect all currencies used in expenses/settlements
    has_member_preferences = any(m.get("settlementCurrency") for m in members)
    rates_target = trip.settlement_currency or (trip_currency if has_member_preferences else None)

    rates_dict = None
    if rates_target:
        all_currencies = set(net_balances.keys())
        # Also include member settlement currencies
        for m in members:
            sc = m.get("settlementCurrency")
            if sc:
                all_currencies.add(sc)

        rates, rate_date = get_rates_for_currencies(db, rates_target, list(all_currencies))
        rates_dict = {
            "target": rates_target,
            "rates": rates,
        }
        exchange_rates_response = {
            "target": rates_target,
            "rates": rates,
            "date": rate_date.isoformat() if rate_date else None,
        }

    if is_consolidated and rates_dict:
        debts = simplify_debts_in_currency(
            net_balances, settled_by, trip.settlement_currency, rates_dict, members
        )
        consolidated_balances = convert_balances_to_currency(
            net_balances, trip.settlement_currency, rates_dict
        )
    else:
        debts = simplify_debts(net_balances, settled_by, members, rates_dict)

    return {
        "netBalances": net_balances,
        "debts": debts,
        "settledByMap": settled_by,
        "consolidatedBalances": consolidated_balances,
        "exchangeRates": exchange_rates_response,
    }
