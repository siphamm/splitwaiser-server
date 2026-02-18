from typing import Protocol

from pydantic import BaseModel


class ReceiptLineItem(BaseModel):
    description: str
    amount: float  # display units (e.g. 12.50 for $12.50)
    quantity: int | None = None


class ReceiptExtractionResult(BaseModel):
    title: str | None = None  # best-guess description (e.g. "Ciao restaurant dinner")
    line_items: list[ReceiptLineItem]
    subtotal: float | None = None  # sum of all line item amounts before extras
    tax: float | None = None  # tax amount
    tips: float | None = None  # tips / gratuity amount
    discount: float | None = None  # discount amount (positive number representing money off)
    fees: float | None = None  # service charges, fees, and any other non-item charges
    total: float | None = None  # grand total of the receipt (the final amount paid)
    currency: str | None = None  # ISO 4217 currency code (e.g. "USD", "JPY")


class ReceiptExtractor(Protocol):
    async def extract(self, image_bytes: bytes, content_type: str, language: str = "en", fallback_currency: str = "USD") -> ReceiptExtractionResult: ...
