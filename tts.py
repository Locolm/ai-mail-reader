import pyttsx3
from bs4 import BeautifulSoup
import re
import atexit

class TTS:

    def __init__(self, preference = "hortense", log_tts=True, print_text=True):
        self.engine = pyttsx3.init()
        self.preference = preference
        self.print_text = True  # Set to True to print text being read
        self.log_tts = True   # Set to True to log TTS events
        self.set_voice(preference)
        atexit.register(self.stop_engine)

    def stop_engine(self):
        """Stop the TTS engine gracefully on exit"""
        try:
            self.engine.stop()
            print("\n[TTS] Engine TTS stopped.")
        except:
            pass

    def set_voice(self, preference):
        # ... (Logique inchangée)
        voices = self.engine.getProperty('voices')
        voice_id = None
        for voice in voices:
            if preference.lower() in voice.name.lower():
                voice_id = voice.id
                break
        if voice_id:
             self.engine.setProperty('voice', voice_id)
             if self.log_tts:
                print(f"[TTS] voice changed to: {self.engine.getProperty('voice')}")
        else:
            if self.log_tts:
                print(f"[TTS] No voice matching '{preference}' found. voice is set by default.")
        
    def clean_text_for_tts(self, text):
        """Clean text to avoid reading gibberish or unwanted patterns."""
        patterns = [
            re.compile(r'[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]{5,}'),
            re.compile(r'[^\sa-zA-Z0-9]{5,}'),
            re.compile(r'\S{40,}')
        ]
        for pattern in patterns:
            if pattern.search(text):
                if self.log_tts:
                    print(f"Skipping incoherent content: '{text}'")
                return ""
        return text


    def say(self, text,is_html=False):
        """
        Read the provided text using TTS. True if something was read, False otherwise.
        """
        if is_html:
            text_blocks_to_queue = []
            processed_blocks = set()
            soup = BeautifulSoup(text, 'html.parser')
            elements = soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'ul', 'li', 'img'])
            if not elements:
                block_to_say = soup.get_text(separator=' ', strip=True)
                if self.print_text:
                    print(block_to_say)
                if block_to_say:
                    cleaned_text = self.clean_text_for_tts(block_to_say)
                    if cleaned_text and cleaned_text not in processed_blocks:
                        text_blocks_to_queue.append(cleaned_text)
                        processed_blocks.add(cleaned_text)
            else:
                for element in elements:
                    block_to_say = ""
                    
                    if element.name == 'img':
                        alt_text = element.get('alt')
                        is_tracking_pixel = (alt_text == "") or (element.get('width') == '1' and element.get('height') == '1')
                        if not is_tracking_pixel and alt_text:
                            block_to_say = f"description d'une image: {alt_text}"
                    else:
                        block_to_say = element.get_text(separator=' ', strip=True)

                if block_to_say:
                    cleaned_text = self.clean_text_for_tts(block_to_say)
                    if cleaned_text and cleaned_text not in processed_blocks:
                        text_blocks_to_queue.append(cleaned_text)
                        processed_blocks.add(cleaned_text)

            final_text = ", ".join(text_blocks_to_queue)
        else:
            final_text = self.clean_text_for_tts(text)
        
        if final_text:
            if self.log_tts:
                print(f"[TTS] Reading: {final_text}")
            
            # BLOQUE L'EXÉCUTION JUSQU'À LA FIN DE LA LECTURE
            self.engine.say(final_text)
            self.engine.runAndWait() 
            return True
        return False

    def list_voices(self):
        """Prints all available voices on the system."""
        voices = self.engine.getProperty('voices')
        print("Available voices:")
        for i, voice in enumerate(voices):
            print(f" Voice {i}: ID={voice.id}, Name='{voice.name}'")
        
if __name__ == "__main__":
    TTS_instance = TTS(preference="hortense")
    TTS_instance.list_voices()
    TTS_instance.say("Bonjour, je suis prêt à lire vos emails")
    print("TTS test completed.")
