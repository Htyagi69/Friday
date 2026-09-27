import os
import json
import firebase_admin
from firebase_admin import credentials,messaging

firebase_json=os.environ["FIREBASE_CONNECTORS"]

cred=credentials.Certificate(json.loads(firebase_json))

firebase_admin.initialize_app(cred)

def send_notification(token:str,title:str,body:str):
    message=messaging.Message(
        notification=messaging.Notification(
        title=title,
        body=body,
        ),
        token=token,
    )

    return messaging.send(message)

