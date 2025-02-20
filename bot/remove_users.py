import requests

from config import BOT_TOKEN, CHANNEL_ID

from .payments import process_payment


def remove_user_from_channel(user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/kickChatMember"

    requests.post(url, json={"chat_id": CHANNEL_ID, "user_id": user_id})


def check_payments():
    users = lambda: ()
    for user in users:
        user_id, card_number, last_payment = user
        success, _ = process_payment(user_id, card_number)

        if not success:
            remove_user_from_channel(user_id)
