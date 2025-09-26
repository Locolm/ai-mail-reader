import pyttsx3
from bs4 import BeautifulSoup
import re

class TTS:

    def __init__(self, preference = "hortense", log_tts=True):
        self.preference = preference
        self.log_tts = log_tts
    
    def speak(self, text):
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        for voice in voices:
            if self.preference.lower() in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break        
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        
    def clean_text_for_tts(self, text: str) -> str:
        """
        Clean the text to make it more suitable for TTS.
        """
        if not text:
            return ""

        segments = re.split(r'[.,;]\s*', text)

        seen = set()
        cleaned_segments = []

        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue

            # --- Cleaning ---
            words = []
            for word in seg.split():
                if re.search(r'[bcdfghjklmnpqrstvwxyz]{10,}', word, re.I):
                    continue
                if re.search(r'[^\wÀ-ÖØ-öø-ÿ]{5,}', word):
                    continue
                if len(word) > 40:
                    continue
                words.append(word)

            seg = " ".join(words).strip()
            if not seg:
                continue

            # --- remove duplicate ---
            if seg not in seen:
                seen.add(seg)
                cleaned_segments.append(seg)
            else:
                if self.log_tts:
                    print(f"[TTS] Removing duplicate inside block: '{seg}'")

        return ". ".join(cleaned_segments)

    def say(self, text,is_html=False):
        """
        Read the provided text using TTS. True if something was read, False otherwise.
        """
        if is_html:
            text_blocks_to_queue = []
            seen_texts = set()
            soup = BeautifulSoup(text, 'html.parser')
            elements = soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'li', 'td', 'img'])
            if not elements:
                block_to_say = soup.get_text(separator=' ', strip=True)
                if block_to_say:
                    cleaned_text = self.clean_text_for_tts(block_to_say)
                    if cleaned_text and cleaned_text not in seen_texts:
                        text_blocks_to_queue.append(cleaned_text)
                        seen_texts.add(cleaned_text)
            else:
                for element in elements:
                    block_to_say = ""
                    
                    if element.name == 'img':
                        alt_text = element.get('alt')
                        is_tracking_pixel = (alt_text == "") or (element.get('width') == '1' and element.get('height') == '1')
                        if not is_tracking_pixel and alt_text:
                            block_to_say = f"description d'une image: {alt_text}"
                    else:
                        block_to_say = "".join([t for t in element.contents if isinstance(t, str)]).strip()

                    if block_to_say:
                        cleaned_text = self.clean_text_for_tts(block_to_say)
                        if cleaned_text and cleaned_text not in seen_texts:
                            text_blocks_to_queue.append(cleaned_text)
                            seen_texts.add(cleaned_text)
            
            if text_blocks_to_queue:
                final_text = self.clean_text_for_tts(soup.get_text(separator=' ', strip=True))
            else:
                final_text = ". ".join(text_blocks_to_queue)
        else:
            final_text = self.clean_text_for_tts(text)
        
        if final_text:
            if self.log_tts:
                print(f"[TTS] Reading: {final_text}")
            self.speak(final_text)
            return True
        return False

    def list_voices(self):
        """Prints all available voices on the system."""
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        engine.stop()
        print("Available voices:")
        for i, voice in enumerate(voices):
            print(f" Voice {i}: ID={voice.id}, Name='{voice.name}'")
        
if __name__ == "__main__":
    TTS_instance = TTS(preference="hortense")
    TTS_instance.list_voices()
    test = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Exemple Simple de Lecture d'E-mail</title>
</head>
<body>

    <h1>Confirmation de Commande et Détails</h1>
    
    <p>Cher(ère) client(e),</p>

    <p>Nous vous remercions de votre récente commande. Vous trouverez ci-dessous le récapitulatif des articles ainsi que les informations de livraison.</p>

    <h2>Articles commandés :</h2>
    
    <ul>
        <li><strong>Article 1 :</strong> Ordinateur Portable X200 - Quantité : 1</li>
        <li><strong>Article 2 :</strong> Souris sans fil Ergonomique - Quantité : 1</li>
        <li><strong>Article 3 :</strong> Tapis de Souris XXL - Quantité : 2</li>
    </ul>

    <h3>Informations de Contact :</h3>
    
    <div style="background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc;">
        <p><strong>Adresse de Livraison :</strong> 123 Rue du Code, 75001 Paris</p>
        <p><strong>Date de Livraison Estimée :</strong> 28 Septembre 2025</p>
    </div>

    <img src="logo_entreprise.png" alt="Logo de l'entreprise" width="100" height="50">

    <div>Cordialement,</div>
    <p>L'Équipe Support</p>

</body>
</html>"""
    TTS_instance.say("Bonjour, je suis prêt à lire vos emails")
    TTS_instance.say("j'attends vos instructions. j'attends vos instructions. j'attends vos instructions.")

    
    TTS_instance.say("Voici un test de la synthèse vocale avec différents types de contenu.")
    TTS_instance.say(test, is_html=True)
    TTS_instance.say("Si je dis ces mots c'est que tout fonctionne correctement.")
    
    print("TTS test completed.")
