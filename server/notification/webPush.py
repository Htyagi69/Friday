import firebase_admin
from firebase_admin import credentials,messaging

cred=credentials.Certificate('firebase.json')

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


# BHeElUz3rChHIJTwCsdL5H8rbVsmGZgXbpSmJxwTANdDARlendA_TsaCsdg9IWK8ikVyT3GPamItTARYVpac2lk