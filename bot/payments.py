import requests


def process_payment(user_id, card_number):
    response = requests.post(
        "https://api.payme.uz/pay",
        json={
            "card": card_number,
            "user_id": user_id,
            # "amount": COURSE_PRICE,
        },
        # headers={"Authorization": f"Bearer {PAYME_API_KEY}"},
    )

    data = response.json()

    if data.get("status") == "success":
        return True, data["join_link"]

    return False, None
