import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from telegram import Update

from .bot import dispatcher, updater


@csrf_exempt
def telegram_webhook(request):
    if request.method == "POST":

        payload = json.loads(request.body)
        update = Update.de_json(payload, updater.bot)

        dispatcher.process_update(update)

        return JsonResponse({"status": "ok"})
    else:
        return JsonResponse({"error": "Invalid request method"}, status=400)
