import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_trip_by_token, verify_creator
from app.receipt.factory import get_receipt_extractor


def _parse_language(accept_language: str | None) -> str:
    """Extract the primary language code from an Accept-Language header."""
    if not accept_language:
        return "en"
    # Take the first language tag, e.g. "vi,en-US;q=0.9" -> "vi"
    primary = accept_language.split(",")[0].split(";")[0].strip()
    return primary or "en"

logger = logging.getLogger("yoyo")
router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}


@router.post("/scan-receipt")
async def scan_receipt_standalone(
    file: UploadFile = File(...),
    accept_language: str | None = Header(None),
    fallback_currency: str = Query("USD"),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image format. Use JPEG, PNG, or WebP.")

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Image too large. Maximum size is 10 MB.")

    language = _parse_language(accept_language)

    try:
        extractor = get_receipt_extractor()
        result = await extractor.extract(image_bytes, file.content_type, language=language, fallback_currency=fallback_currency)
    except ValueError as e:
        logger.error(f"Receipt extraction config error: {e}")
        raise HTTPException(status_code=503, detail="Receipt scanning is not available")
    except Exception as e:
        logger.error(f"Receipt extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Failed to extract receipt data. Please try again.")

    logger.info("Standalone receipt scanned", extra={"extra_data": {"items_count": len(result.line_items)}})

    return {
        "title": result.title,
        "lineItems": [
            {"description": item.description, "amount": item.amount, "quantity": item.quantity}
            for item in result.line_items
        ],
        "total": result.total,
        "extras": result.extras,
        "currency": result.currency,
    }


@router.post("/trips/{access_token}/scan-receipt")
async def scan_receipt(
    access_token: str,
    request: Request,
    file: UploadFile = File(...),
    accept_language: str | None = Header(None),
    db: Session = Depends(get_db),
):
    trip = get_trip_by_token(access_token, db)
    if not trip.allow_member_edit_expenses:
        verify_creator(trip, request, db)

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image format. Use JPEG, PNG, or WebP.")

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Image too large. Maximum size is 10 MB.")

    language = _parse_language(accept_language)

    try:
        extractor = get_receipt_extractor()
        result = await extractor.extract(image_bytes, file.content_type, language=language, fallback_currency=trip.currency)
    except ValueError as e:
        logger.error(f"Receipt extraction config error: {e}")
        raise HTTPException(status_code=503, detail="Receipt scanning is not available")
    except Exception as e:
        logger.error(f"Receipt extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Failed to extract receipt data. Please try again.")

    logger.info(
        "Receipt scanned",
        extra={"extra_data": {"trip_id": trip.id, "items_count": len(result.line_items)}},
    )

    return {
        "title": result.title,
        "lineItems": [
            {"description": item.description, "amount": item.amount, "quantity": item.quantity}
            for item in result.line_items
        ],
        "total": result.total,
        "extras": result.extras,
        "currency": result.currency,
    }
