import os
import resend


def send_trip_link(email: str, trip_name: str, access_token: str):
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        return

    resend.api_key = api_key
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    trip_url = f"{frontend_url}/trip/{access_token}"

    resend.Emails.send({
        "from": "Yoyo App <hello@getyoyo.co>",
        "to": [email],
        "subject": f"Details for your trip: {trip_name}",
        "html": (
            f"<p>Your trip <strong>{trip_name}</strong> has been created!</p>"
            f'<p><a href="{trip_url}">Click here to view your trip</a></p>'
            f"<p style=\"color:#888;font-size:12px\">Please bookmark this link — it's the only way to access your trip.</p>"
            f"<p>Happy traveling!</p>"
        ),
    })
