from __future__ import print_function
import os.path
import base64
import traceback

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError
import locale
from datetime import datetime, timezone

from input_system import InputSystem
from tts import TTS
import logging

import utils

logging.getLogger("comtypes").setLevel(logging.CRITICAL)

class gmailClient:

    def __init__(self, tts_instance = TTS(preference="hortense"),  voice=True, scopes=None, secrets_dir="secrets", token_file="token.json", credentials_file="credentials.json"):
        if scopes is not None:
            self.scopes = scopes
        else:
            self.scopes = ["https://www.googleapis.com/auth/gmail.modify"]
        
        self.service = self.get_service(secrets_dir=secrets_dir, token_file=token_file, credentials_file=credentials_file)
        
        self.tts_instance = tts_instance
        self.input_system = InputSystem(tts_instance=self.tts_instance, voice=voice)

    def get_service(self, secrets_dir="secrets", token_file="token.json", credentials_file="credentials.json"):
        """Handles auth and returns a Gmail API service object."""
        creds = None
        token_path = os.path.join(secrets_dir, token_file)
        credentials_path = os.path.join(secrets_dir, credentials_file)
        
        if not os.path.exists(secrets_dir):
            os.makedirs(secrets_dir)
            
        try:        
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, self.scopes)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, self.scopes)
                    creds = flow.run_local_server(port=0)
                with open(token_path, "w") as token:
                    token.write(creds.to_json())
            return build("gmail", "v1", credentials=creds)
        except RefreshError as e:
            print("[INFO] Token expiré ou révoqué. Suppression de token.json et reconnexion...")
            if os.path.exists(token_path):
                os.remove(token_path)
            return self.get_service(secrets_dir=secrets_dir, token_file=token_file, credentials_file=credentials_file)


    def count_exact_unread_conversations(self):
        """
        Counts the exact number of unread conversations with filters.
        """
        query = "is:unread label:INBOX -category:promotions -category:social"
        count = 0
        page_token = None
        
        while True:
            results = self.service.users().threads().list(
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

    def list_unread_titles(self):
        """
        Lists subject and expeditor of unread conversations (light version).
        Only fetches minimal metadata to reduce API usage.
        """
        query = "is:unread label:INBOX -category:promotions -category:social"
        page_token = None

        while True:
            results = self.service.users().messages().list(
                userId="me",
                q=query,
                pageToken=page_token
            ).execute()

            messages = results.get("messages", [])
            if not messages:
                break

            for m in messages:
                msg = self.service.users().messages().get(
                    userId="me",
                    id=m["id"],
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]
                ).execute()

                headers = msg["payload"]["headers"]
                sender = next((h["value"] for h in headers if h["name"] == "From"), "")
                subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
                date_str = next((h["value"] for h in headers if h["name"] == "Date"), "")
                recieved = utils.format_gmail_date(date_str,msg.get("internalDate"))

                yield {
                    "id": m["id"],
                    "from": sender,
                    "subject": subject,
                    "date": recieved
                }

            page_token = results.get("nextPageToken")
            if not page_token:
                break

    def list_unread_conversations(self):
        """
        Generator that iterates through unread conversations (with pagination)
        and returns a structure with message details and content.
        """
        query = "is:unread label:INBOX -category:promotions -category:social"
        page_token = None
        
        while True:
            results = self.service.users().threads().list(
                userId="me", 
                q=query,
                pageToken=page_token
            ).execute()
            
            threads = results.get("threads", [])
            
            if not threads:
                break
                
            for thread in threads:
                thread_id = thread["id"]
                t = self.service.users().threads().get(userId="me", id=thread_id).execute()
                
                conversation_messages = []
                
                for msg in t["messages"]:
                    headers = msg["payload"]["headers"]
                    sender = next((h["value"] for h in headers if h["name"] == "From"), "")
                    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
                    date_str = next((h["value"] for h in headers if h["name"] == "Date"), "")
                    recieved = utils.format_gmail_date(date_str,msg.get("internalDate"))
                    
                    conversation_messages.append({
                        "from": sender,
                        "subject": subject,
                        "date": recieved,
                        "content": utils.get_message_content(msg)
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

    def mark_thread_as_read(self, thread_id: str):
        """
        Marks a conversation (thread) as read by removing the UNREAD label.
        """
        self.service.users().threads().modify(
            userId="me",
            id=thread_id,
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()

    def mark_all_unread_as_read(self, unread_items):
        """
        Marks all unread conversations as read.
        """

        self.tts_instance.say(f"Marquage de toutes les conversations non lues comme lues.")
        
        for item in unread_items:
            thread_id = item.get("id")
            if thread_id:
                try:
                    self.mark_thread_as_read(thread_id)
                    print(f"Conversation {thread_id} marquée comme lue.")
                except Exception as e:
                    print(f"Erreur lors du marquage de {thread_id} : {e}")

    def read_messages(self, unread_items):
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

            self.tts_instance.say(", ".join(p for p in meta_parts if p))

            if "messages" not in conv:
                # --- Case without messages ---   
                self.tts_instance.say("Aucun message dans cette conversation.")    
                command = self.input_system.get_command(type=0)
                print(f"[DEBUG] Commande reçue: '{command}'")
                
                if command == 'q':
                    print("Arrêt de la lecture.")
                    return
                continue
            else:
                # --- Case message : navigation inside conversation ---
                command = self.input_system.get_command(type=2)
                print(f"[DEBUG] Commande reçue: '{command}'")
                
                if command == 'q':
                    print("Arrêt de la lecture.")
                    return

                if command == 'r':
                    self.mark_thread_as_read(conv["id"])
                    self.tts_instance.say("Conversation marquée comme lue.")
                    messages = conv["messages"]
                    msg_index = 0
                    while msg_index < len(messages):
                        msg = messages[msg_index]

                        # En-tête du message
                        msg_header = f"Message {msg_index + 1} sur {len(messages)}. De: {msg.get('from', '')}"
                        self.tts_instance.say(msg_header)

                        # Contenu du message
                        content_read = self.tts_instance.say(msg.get("content", ""), is_html=True)
                        if not content_read:
                            self.tts_instance.say("Contenu du message introuvable ou non pertinent.")

                        # Attente commande navigation
                        command = self.input_system.get_command(type=1)
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
                            self.tts_instance.say("Commande non reconnue. Lecture du message suivant.")
                            msg_index += 1

        if not any_item:
            self.tts_instance.say("Aucune conversation non lue à lire.")
        else:
            self.tts_instance.say("Fin de toutes les conversations non lues.")


    def get_unread_filtered(self, subject=None, sender=None, date=None):
        """
        Returns a list of unread conversations filtered by subject, sender, or date.
        Parameters can be partial and case-insensitive.
        """
        filtered = []
        for item in self.list_unread_titles():
            match = True
            if subject and subject.lower() not in item.get("subject", "").lower():
                match = False
            if sender and sender.lower() not in item.get("from", "").lower():
                match = False
            if date and date.lower() not in item.get("date", "").lower():
                match = False
            if match:
                filtered.append(item)
        return filtered

    def send_message(self, to, subject, body):
        pass

    def respond_to_message(self, message_id):
        pass

    def delete_message(self, message_id):
        pass

    def delete_conversation(self, thread_id):
        pass

    def mark_as_unread(self, message_id):
        pass

if __name__ == "__main__":
    try:       
        tts_instance = TTS(preference="hortense")
        
        gmail_client_instance = gmailClient(tts_instance=tts_instance, voice=True)
        
        unread_count = gmail_client_instance.count_exact_unread_conversations()
        
        tts_instance.say(f"Bonjour. Vous avez {unread_count} conversations non lues.")
        
        if unread_count > 0:
            unread = gmail_client_instance.list_unread_conversations()
            gmail_client_instance.read_messages(unread)
            
            # mark all conversations as read
            # unread = gmail_client_instance.list_unread_titles()
            # gmail_client_instance.mark_all_unread_as_read(unread)
        
    except KeyboardInterrupt:
        print("\nArrêt du programme.") 
    except Exception as e:
        traceback.print_exc()