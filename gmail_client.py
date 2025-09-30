from __future__ import print_function
import os.path
import base64

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import locale
from datetime import datetime, timezone

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
    if part.get("mimeType") == "text/html":
        if "data" in part["body"]:
            decoded_html = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
            return decoded_html

    # Fallback to plain text if no HTML part is found
    if part.get("mimeType") == "text/plain":
        if "data" in part["body"]:
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
    
    # Handle multipart messages recursively
    if part.get("parts"):
        for sub_part in part["parts"]:
            content = get_part_content(sub_part)
            if content:
                return content
    
    return ""

def get_message_content(message):
    """
    Extracts and decodes the message body, handling complex structures.
    """
    return get_part_content(message["payload"])


def format_gmail_date(date_str: str = None, internal_date: str = None) -> str:
    """
    Formats Gmail date strings or internal timestamps into a human-readable format.
    Prioritizes internal_date if both are provided.
    """
    try:
        if internal_date:
            ts = int(internal_date) / 1000  # ms conversion to s
            dt = datetime.fromtimestamp(ts).astimezone()
        elif date_str:
            # Gmail "Date" header ex: 'Mon, 30 Sep 2025 12:32:00 +0000'
            dt = datetime.strptime(date_str[:-6], "%a, %d %b %Y %H:%M:%S").astimezone()
        else:
            return ""
        
        # Force in french locale for month names
        # locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
        return dt.strftime("Reçu le %d %B %Y à %Hh%M")

    except Exception:
        return ""


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

def list_unread_titles():
    """
    Lists subject and expeditor of unread conversations (light version).
    Only fetches minimal metadata to reduce API usage.
    """
    service = get_service()
    query = "is:unread label:INBOX -category:promotions -category:social"
    page_token = None

    while True:
        results = service.users().messages().list(
            userId="me",
            q=query,
            pageToken=page_token
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            break

        for m in messages:
            msg = service.users().messages().get(
                userId="me",
                id=m["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()

            headers = msg["payload"]["headers"]
            sender = next((h["value"] for h in headers if h["name"] == "From"), "")
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
            date_str = next((h["value"] for h in headers if h["name"] == "Date"), "")
            recieved = format_gmail_date(date_str,msg.get("internalDate"))

            yield {
                "id": m["id"],
                "from": sender,
                "subject": subject,
                "date": recieved
            }

        page_token = results.get("nextPageToken")
        if not page_token:
            break

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
                date_str = next((h["value"] for h in headers if h["name"] == "Date"), "")
                recieved = format_gmail_date(date_str,msg.get("internalDate"))
                
                conversation_messages.append({
                    "from": sender,
                    "subject": subject,
                    "date": recieved,
                    "content": get_message_content(msg)
                })
            
            yield {
                "id": thread_id,
                "first_message_from": conversation_messages[0]["from"],
                "subject": conversation_messages[0]["subject"],
                "date": conversation_messages[0]["date"],
                "messages": conversation_messages
            }
            
        page_token = results.get("nextPageToken")
        
        if not page_token:
            break

def mark_thread_as_read(thread_id: str):
    """
    Marks a conversation (thread) as read by removing the UNREAD label.
    """
    service = get_service()
    
    service.users().threads().modify(
        userId="me",
        id=thread_id,
        body={"removeLabelIds": ["UNREAD"]}
    ).execute()

def mark_all_unread_as_read(unread_items, tts_instance= None):
    """
    Marks all unread conversations as read.
    """
    if tts_instance:
        tts_instance.say(f"Marquage de toutes les conversations non lues comme lues.")
    
    for item in unread_items:
        thread_id = item.get("id")
        if thread_id:
            try:
                mark_thread_as_read(thread_id)
                print(f"Conversation {thread_id} marquée comme lue.")
            except Exception as e:
                print(f"Erreur lors du marquage de {thread_id} : {e}")

def read_messages(tts_instance, unread_items, voice=True):
    """
    Reads out loud the list of unread conversations and their messages.
    Allows navigation through messages and conversations via commands.
    Parameters:
    - tts_instance: An instance of the TTS class for text-to
        speech conversion.
    - unread_items: A list of unread conversations to read.
    - voice: If True, uses voice recognition for commands; otherwise, uses text input.
    """
    any_item = False

    for conv_index, conv in enumerate(unread_items, start=1):
        any_item = True

        # --- Metadata conversation ---
        meta_parts = [
            f"Conversation {conv_index}.",
            f"Expéditeur: {conv.get('first_message_from') or conv.get('from', '')}",
            f"Sujet: {conv.get('subject', '(sans sujet)')}",
            f"{conv.get('date', '')}"
        ]

        if "messages" in conv:
            meta_parts.append(f"Contient {len(conv['messages'])} messages.")

        tts_instance.say(", ".join(p for p in meta_parts if p))

        if "messages" not in conv:
            # --- Case without messages ---   
            tts_instance.say("Aucun message dans cette conversation.")    
            command = get_command(voice, type=0, tts_instance=tts_instance)
            print(f"[DEBUG] Commande reçue: '{command}'")
            
            if command == 'q':
                print("Arrêt de la lecture.")
                return
            continue
        else:
            # --- Case message : navigation inside conversation ---
            command = get_command(voice, type=2, tts_instance=tts_instance)
            print(f"[DEBUG] Commande reçue: '{command}'")
            
            if command == 'q':
                print("Arrêt de la lecture.")
                return

            if command == 'r':
                mark_thread_as_read(conv["id"])
                tts_instance.say("Conversation marquée comme lue.")
                messages = conv["messages"]
                msg_index = 0
                while msg_index < len(messages):
                    msg = messages[msg_index]

                    # En-tête du message
                    msg_header = f"Message {msg_index + 1} sur {len(messages)}. De: {msg.get('from', '')}"
                    tts_instance.say(msg_header)

                    # Contenu du message
                    content_read = tts_instance.say(msg.get("content", ""), is_html=True)
                    if not content_read:
                        tts_instance.say("Contenu du message introuvable ou non pertinent.")

                    # Attente commande navigation
                    command = get_command(voice, type=1, tts_instance=tts_instance)
                    print(f"[DEBUG] Commande reçue: '{command}'")

                    if command == 'q':
                        print("Arrêt de la lecture.")
                        return
                    elif command == 'n':
                        msg_index += 1
                    elif command == 'p':
                        msg_index = max(0, msg_index - 1)
                    elif command == 'c':
                        break
                    else:
                        tts_instance.say("Commande non reconnue. Lecture du message suivant.")
                        msg_index += 1

    if not any_item:
        tts_instance.say("Aucune conversation non lue à lire.")
    else:
        tts_instance.say("Fin de toutes les conversations non lues.")


def get_command(voice: bool, type: int = 1, tts_instance=None) -> str:
    """
    Obtains a command from user input or voice recognition.
    
    Types:
      0 = simple navigation: next, quit
      1 = conversation navigation: next, previous, next conversation, quit, read
      2 = extended navigation: next, previous, read, quit

    Returns:
      'n' = next
      'p' = previous
      'c' = next conversation
      'r' = read/relire
      'q' = quit
      ''  = unrecognized
    """

    # --- Command sets ---
    COMMANDS = {
        0: {
            "n": ["n", "suivant"],
            "q": ["q", "quitter"]
        },
        1: {
            "n": ["n", "suivant"],
            "p": ["p", "précédent"],
            "c": ["c", "continuer", "message"],
            "q": ["q", "quitter"]
        },
        2: {
            "n": ["n", "suivant"],
            "p": ["p", "précédent"],
            "r": ["r", "lecture", "lire", "relire"],
            "q": ["q", "quitter"]
        }
    }

    HELP_TEXT = {
        0: "Commandes disponibles : suivant, quitter.",
        1: "Commandes disponibles : suivant, précédent, message, quitter.",
        2: "Commandes disponibles : suivant, précédent, lecture, quitter."
    }

    commands = COMMANDS.get(type, {})

    if not voice:
        # Mode clavier
        prompt = f"\n[Commande] {HELP_TEXT[type]} → "
        cmd = input(prompt).lower().strip()
        return cmd if cmd in commands else ""
    else:
        # Mode vocal
        if tts_instance:
            tts_instance.say(f"Vous pouvez dire : {HELP_TEXT[type]}")
        cmd = voice_input(prompt="Votre commande...").lower().strip()

        if "commande" in cmd or "aide" in cmd or "options" in cmd:
            if tts_instance:
                tts_instance.say(HELP_TEXT[type])
            cmd = voice_input(prompt="Votre commande...").lower().strip()

        cmd_words = set(cmd.lower().split())
        for key, synonyms in commands.items():
            if cmd_words.intersection(set(s.lower() for s in synonyms)):
                return key  
    return ""



if __name__ == "__main__":
    try:
        TTS_instance = TTS(preference="hortense")
        
        unread_count = count_exact_unread_conversations()
        
        TTS_instance.say(f"Bonjour. Vous avez {unread_count} conversations non lues.")
        
        if unread_count > 0:
            unread = list_unread_conversations()
            read_messages(TTS_instance, unread)
            
            # mark all conversations as read
            # unread = list_unread_titles()
            # mark_all_unread_as_read(unread, tts_instance=TTS_instance)
        
    except KeyboardInterrupt:
        print("\nArrêt du programme.") 
    except Exception as e:
        print(f"Une erreur s'est produite: {e}")