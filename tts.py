import pyttsx3
import time
from bs4 import BeautifulSoup
import re

def clean_text_for_tts(text):
    """
    Cleans text to remove incoherent blocks before sending to TTS.
    Returns a cleaned string or an empty string if it's too incoherent.
    """
    # Define patterns for incoherent content
    patterns = [
        re.compile(r'[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]{5,}'), # 5+ consecutive consonants
        re.compile(r'\d{10,}'), # 10+ consecutive digits (e.g., phone numbers, long IDs)
        re.compile(r'[^\sa-zA-Z0-9]{5,}'), # 5+ consecutive special characters
        re.compile(r'\S{40,}') # 40+ non-whitespace characters (long URLs, gibberish)
    ]

    # Check for incoherent patterns
    for pattern in patterns:
        if pattern.search(text):
            print(f"Skipping incoherent content: '{text}'")
            return "Contenu non pertinent."

    return text

def say(text, preference = "hortense", print_text=True):
        
    engine = pyttsx3.init()
    
    # voice selection
    voices = engine.getProperty('voices')
    voice_id = None
    for voice in voices:
        # Check if the voice is a female voice (this depends on the system's voice naming conventions)
        if preference in voice.name.lower():
            voice_id = voice.id
            break
    
    # If a female voice is found, set it
    if voice_id:
        engine.setProperty('voice', voice_id)
    else:
        print("No voice found. Using default voice.")
        
    is_html = bool(re.search(r'<[^>]+>', text))
    if is_html:
        # Parse HTML
        soup = BeautifulSoup(text, 'html.parser')
        
        # Extract text
        elements = soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'ul', 'li', 'img'])
        
        if not elements:
            text_to_say = soup.get_text(separator=' ', strip=True)
            if print_text:
                print(text_to_say)
            engine.say(text_to_say)
            engine.runAndWait()
        else:
            for element in elements:
                # image handling
                if element.name == 'img' and element.get('alt'):
                    img_description = f"Image: {element['alt']}"
                    if print_text:
                        print(img_description)
                    engine.say(img_description)
                    engine.runAndWait()
                    time.sleep(0.5)
                    
                else:
                    block_text = element.get_text(separator=' ', strip=True)
                    if block_text:
                        if print_text:
                            print(block_text)
                        engine.say(block_text)
                        engine.runAndWait()
                        time.sleep(0.5) # pause beetween blocks

    else:
        # it's not html
        if print_text:
            print(text)
        engine.say(text)
        engine.runAndWait()
    
def list_voices():
    """Prints all available voices on the system."""
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    print("Available voices:")
    for i, voice in enumerate(voices):
        print(f"  Voice {i}: ID={voice.id}, Name='{voice.name}'")

if __name__ == "__main__":
    list_voices()
    say("Bonjour, je suis prêt à lire vos emails")
    print("TTS test completed.")
