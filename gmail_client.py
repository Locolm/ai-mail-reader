from __future__ import print_function
import os.path
import base64
import re

from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from tts import say

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def get_service():
    """Handles auth and returns a Gmail API service object."""
    creds = None
    
    secrets_dir = "secrets"
    token_path = os.path.join(secrets_dir, "token.json")
    credentials_path = os.path.join(secrets_dir, "credentials.json")
    
    if not os.path.exists(secrets_dir):
        os.makedirs(secrets_dir)
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def get_part_content(part):
    """Recursively processes message parts and returns HTML or plain text content."""
    
    # Prioritize HTML content and return it as-is
    if part.get('mimeType') == 'text/html':
        if 'data' in part['body']:
            decoded_html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            return decoded_html

    # Fallback to plain text if no HTML part is found
    if part.get('mimeType') == 'text/plain':
        if 'data' in part['body']:
            return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
    
    # Handle multipart messages recursively
    if part.get('parts'):
        for sub_part in part['parts']:
            content = get_part_content(sub_part)
            if content:
                return content
    
    return ""

def get_message_content(message):
    """
    Extracts and decodes the message body, handling complex structures.
    """
    return get_part_content(message['payload'])

def count_exact_unread_conversations():
    """
    Counts the exact number of unread conversations with filters.
    """
    service = get_service()
    query = "is:unread label:INBOX -category:promotions -category:social"
    count = 0
    page_token = None
    
    while True:
        results = service.users().threads().list(
            userId="me", 
            q=query,
            pageToken=page_token
        ).execute()
        
        threads = results.get("threads", [])
        count += len(threads)
        page_token = results.get("nextPageToken")
        
        if not page_token:
            break
            
    return count

def list_unread_conversations():
    """
    Generator that iterates through unread conversations (with pagination)
    and returns a structure with message details and content.
    """
    service = get_service()
    query = "is:unread label:INBOX -category:promotions -category:social"
    page_token = None
    
    while True:
        results = service.users().threads().list(
            userId="me", 
            q=query,
            pageToken=page_token
        ).execute()
        
        threads = results.get("threads", [])
        
        if not threads:
            break
            
        for thread in threads:
            thread_id = thread["id"]
            t = service.users().threads().get(userId="me", id=thread_id).execute()
            
            conversation_messages = []
            
            for msg in t["messages"]:
                headers = msg["payload"]["headers"]
                sender = next((h["value"] for h in headers if h["name"] == "From"), "")
                subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
                
                conversation_messages.append({
                    "from": sender,
                    "subject": subject,
                    "content": get_message_content(msg)
                })
            
            yield {
                "id": thread_id,
                "first_message_from": conversation_messages[0]["from"],
                "subject": conversation_messages[0]["subject"],
                "messages": conversation_messages
            }
            
        page_token = results.get("nextPageToken")
        
        if not page_token:
            break

if __name__ == "__main__":
    try:
        unread_count = count_exact_unread_conversations()
        say(f"Vous avez {unread_count} conversations non lues.")
        print("-" * 30)

        print("Liste des conversations non lues:")
        mails_generator = list_unread_conversations()
        for conv in mails_generator:
            try:
                print("-" * 15)
                print(f"Conversation ID: {conv["id"]}")
                say(f"Expéditeur du premier message: {conv["first_message_from"]}")
                say(f"Sujet: {conv["subject"]}")
                say(f"Nombre de messages dans la conversation: {len(conv["messages"])}")
                
                for i, message_data in enumerate(conv["messages"]):
                    try:
                        print(f"--- Message {i+1} ---")
                        say(f"Message {i+1}.")
                        
                        message_content = message_data.get("content", "")
                        if message_content:
                            say(f"Contenu: {message_content}...")
                        else:
                            say("Contenu du message introuvable.")
                        print("-" * 15)   
                    except KeyboardInterrupt:
                        print("\nmessage ignoré.")
    
            except KeyboardInterrupt:
                print("\nConversation ignorée.")
    except KeyboardInterrupt:
        print("\nArrêt du programme.")  
    except Exception as e:
        print(f"Une erreur s'est produite: {e}")