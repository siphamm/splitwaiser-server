import base64
from datetime import datetime, timezone

from agents import Agent, Runner

from app.receipt.base import ReceiptExtractionResult

INSTRUCTIONS = """\
You are a receipt parser. Given a receipt image, extract a title, individual line items, and extras.

Rules:
- title: a short, descriptive name for this receipt. Follow these guidelines:
  - For restaurant/food receipts: use the format "<store name> <meal type>" where meal type is inferred from the receipt time or the current time provided. Use "breakfast" (before 11am), "lunch" (11am-3pm), "dinner" (3pm-9pm), or "late night" (after 9pm). Example: "Ciao restaurant dinner", "McDonald's lunch".
  - For transport receipts: describe the service, e.g. "Uber ride to airport".
  - For other receipts: use "<store name> shopping" or just the store name if obvious. Example: "Target shopping", "7-Eleven snacks".
  - If the store name is not visible, describe based on the items, e.g. "Grocery shopping", "Coffee run".
- line_items: only actual purchased items/products/services with their prices
- amount is the total price for that line item (price * quantity), as a decimal number with full precision
- quantity is optional (null if not visible)
- total: the grand total shown on the receipt (the final amount paid, including everything). null if not visible.
- extras: the sum of ALL non-item charges — tax, tips, service charges, fees, gratuity, etc. Add them all together into one number. null if none found.
- Do NOT include tax/tips/fees/service charges as line_items
- Keep descriptions concise but recognizable
- currency: the ISO 4217 currency code of the receipt (e.g. "USD", "JPY", "EUR"). Infer from currency symbols ($, ¥, €, etc.), country/region clues on the receipt, or the store's known location. If you cannot determine the currency, use the fallback currency provided by the user.
- IMPORTANT: The title and item descriptions MUST be in the language specified by the user."""

agent = Agent(
    name="Receipt Scanner",
    instructions=INSTRUCTIONS,
    model="gpt-4o",
    output_type=ReceiptExtractionResult,
)


class OpenAIReceiptExtractor:
    """Receipt extraction using OpenAI Agents SDK with GPT-4o vision."""

    async def extract(self, image_bytes: bytes, content_type: str, language: str = "en", fallback_currency: str = "USD") -> ReceiptExtractionResult:
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        media_type = content_type or "image/jpeg"
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        prompt = (
            f"Extract line items and total from this receipt. "
            f"The current time is {now_utc}. Use this to infer the meal type if the receipt has no timestamp. "
            f"Respond with the title and descriptions in this language: {language}. "
            f"If you cannot determine the currency from the receipt, use: {fallback_currency}"
        )

        result = await Runner.run(
            agent,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": f"data:{media_type};base64,{b64_image}"},
                    ],
                }
            ],
        )

        return result.final_output
