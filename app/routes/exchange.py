from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_trip_by_token
from app.exchange import get_rates_for_currencies

router = APIRouter()


@router.get("/trips/{access_token}/exchange-rates")
def get_exchange_rates(
    access_token: str,
    target: str = Query(..., description="Target settlement currency"),
    db: Session = Depends(get_db),
):
    if target not in ("USD", "HKD", "JPY"):
        raise HTTPException(status_code=400, detail="Invalid target currency")

    trip = get_trip_by_token(access_token, db)

    # Collect all currencies used in expenses, settlements, and member preferences
    currencies_used: set[str] = set()
    for expense in trip.expenses:
        currencies_used.add(expense.currency or trip.currency)
    for settlement in trip.settlements:
        currencies_used.add(settlement.currency or trip.currency)
    for member in trip.members:
        if member.settlement_currency:
            currencies_used.add(member.settlement_currency)

    # If only one currency is used and it matches target, no rates needed
    if currencies_used <= {target}:
        return {"target": target, "rates": {}, "date": None}

    try:
        rates, rate_date = get_rates_for_currencies(
            db, target, list(currencies_used)
        )
    except Exception:
        raise HTTPException(
            status_code=502, detail="Failed to fetch exchange rates"
        )

    return {
        "target": target,
        "rates": rates,
        "date": rate_date.isoformat() if rate_date else None,
    }
