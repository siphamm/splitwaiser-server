from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Trip, UserTrip
from app.serializers import serialize_trip_summary

router = APIRouter()


@router.get("/me")
def get_me(request: Request):
    user = request.state.user
    if not user:
        return None
    return {"id": user.id, "name": user.name}


@router.get("/me/trips")
def get_my_trips(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return []
    trips = (
        db.query(Trip)
        .join(UserTrip, UserTrip.trip_id == Trip.id)
        .filter(UserTrip.user_id == user.id, Trip.is_deleted == False)  # noqa: E712
        .order_by(UserTrip.last_visited_at.desc())
        .all()
    )
    return [serialize_trip_summary(t) for t in trips]


@router.delete("/me/trips/{access_token}", status_code=204)
def leave_trip(access_token: str, request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    trip = db.query(Trip).filter(Trip.access_token == access_token).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    db.query(UserTrip).filter(
        UserTrip.user_id == user.id,
        UserTrip.trip_id == trip.id,
    ).delete()
    db.commit()
    return None
