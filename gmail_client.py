from __future__ import print_function
import os.path
import base64

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from tts import TTS
import logging

from voice import voice_input

logging.getLogger("comtypes").setLevel(logging.CRITICAL)


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

def read_messages(tts_instance, unread_conversations, voice = True):
    
    conversations = list(unread_conversations)
    if not conversations:
        tts_instance.say("Aucune conversation non lue à lire.")
        return

    conv_index = 0 # Index de la conversation en cours
    msg_index = 0  # Index du message dans la conversation

    while conv_index < len(conversations):
        conv = conversations[conv_index]
        current_messages = conv["messages"]
        
        metadata_blocks = [
            f"Conversation {conv_index + 1} sur {len(conversations)}.",
            f"Expéditeur: {conv['first_message_from']}",
            f"Sujet: {conv['subject']}",
            f"Contient {len(current_messages)} messages."
        ]

        tts_instance.say(", ".join(metadata_blocks))
        
        while msg_index < len(current_messages):
            
            msg_data = current_messages[msg_index]
            
            msg_header = f"Message {msg_index + 1} sur {len(current_messages)}. De: {msg_data['from']}"
            tts_instance.say(msg_header)
            
            content_read = tts_instance.say(msg_data.get("content", ""), is_html=True)
            if not content_read:
                tts_instance.say("Contenu du message introuvable ou non pertinent.")

            if not voice:
                command = input("\n[Commande] Taper (n) pour suivant, (p) pour précédent, (c) pour conversation suivante, (q) pour quitter: ").lower().strip()
            else :
                tts_instance.say("Dites 'suivant', 'précédent', 'conversation suivante' ou 'quitter'.")
                command = voice_input(prompt="Votre commande...").lower().strip()
                if "suivant" in command:
                    command = 'n'
                elif "précédent" in command:
                    command = 'p'
                elif "conversation suivante" in command:
                    command = 'c'
                elif "quitter" in command:
                    command = 'q'
                else:
                    command = ''
            
            if command == 'q':
                print("Arrêt de la lecture.")
                return
            elif command == 'n':
                msg_index += 1 # Message suivant
            elif command == 'p':
                msg_index = max(0, msg_index - 1) # Message précédent
            elif command == 'c':
                break # Sort de la boucle des messages pour passer à la conversation suivante
            else:
                tts_instance.say("Commande non reconnue. Lecture du message suivant.")
                msg_index += 1

        if msg_index >= len(current_messages):
            conv_index += 1
            msg_index = 0

    tts_instance.say("Fin de toutes les conversations non lues.")


if __name__ == "__main__":
    try:
        TTS_instance = TTS(preference="hortense")
        
        unread_count = count_exact_unread_conversations()
        
        TTS_instance.say(f"Bonjour. Vous avez {unread_count} conversations non lues.")
        
        if unread_count > 0:
            unread_conversations = list_unread_conversations()
            read_messages(TTS_instance, unread_conversations)
        
    except KeyboardInterrupt:
        print("\nArrêt du programme.") 
    except Exception as e:
        print(f"Une erreur s'est produite: {e}")