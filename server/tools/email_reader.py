import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


CRENDENTIAL_FILE=json.loads(os.environ["CREDENTIALS"])
TOKEN_FILE=json.loads(os.environ["TOKEN"])

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def get_unread_emails(total_mails,match=None):
    info=""
    creds=None
    if TOKEN_FILE.exists():
        creds=Credentials.from_authorized_user_file(str(TOKEN_FILE),SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("🔐 Starting Gmail OAuth...")
            flow=InstalledAppFlow.from_client_secrets_file(str(CRENDENTIAL_FILE),SCOPES)
            creds=flow.run_local_server(
                port=8080,
                access_type="offline",
                prompt="consent"
                )
        # print("Refresh token:", bool(creds.refresh_token))
        TOKEN_FILE.write_text(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        results = service.users().messages().list(userId="me",q="is:unread",maxResults=total_mails).execute()
        messages=results.get("messages",[])

        if not messages:
            print("No unread email found")
            return "You have no unread emails."
        print(f"Found {len(messages)} unread email\n"+"="*40)
     
        for msg in messages:
            message=service.users().messages().get(userId="me", id=msg["id"]).execute()
            headers=message.get("payload",{}).get("headers",[])

            subject=next((h["value"] for h in headers if h["name"]== "Subject"),"No Subject")
            sender=next((h["value"] for h in headers if h["name"]== "From"),"Unknown Sender")
            snippet=message.get("snippet", "No preview available")
            # print(f"From:{sender}\nSubject:{subject}\nSnippet:{snippet}"+"-"*40)
            info+=(f"From:{sender}\nSubject:{subject}\nSnippet:{snippet}"+"-"*40)
        print(info)
        return info
    except HttpError as error:
    # TODO(developer) - Handle errors from gmail API.
       print(f"An error occurred: {error}")
       return f"Failed to fetch emails: {error}"



