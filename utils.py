import base64
import datetime

@staticmethod
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

@staticmethod
def get_message_content(message):
    """
    Extracts and decodes the message body, handling complex structures.
    """
    return get_part_content(message["payload"])

@staticmethod
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