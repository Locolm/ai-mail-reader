from tts import TTS
import speech_recognition as sr


class InputSystem:
    def __init__(self, tts_instance=TTS(preference="hortense"), voice=True, help_activated = True):
        self.tts_instance = tts_instance # Instance of TTS class for voice feedback
        self.voice = voice # True for voice input, False for keyboard input
        self.help_activated = help_activated  # set to False to not have a recall of commands at each input
        self.commands = {
            0: {
                "n": ["n", "suivant"],
                "q": ["q", "quitter"]
            },
            1: {
                "n": ["n", "suivant"],
                "p": ["p", "précédent"],
                "c": ["c", "continuer", "sortir", "conversation"], # next conversation
                "a":["répondre","répond","réponse", "repondre", "repond", "reponse"],
                "q": ["q", "quitter"]
            },
            2: {
                "n": ["n", "suivant"],
                "p": ["p", "précédent"],
                "r": ["r", "lecture", "lire", "relire"],
                "q": ["q", "quitter"]
            },
            3: {
                "y": ["oui", "ouais", "yes", "yep", "affirmatif"],
                "n": ["non", "no", "nop", "negative"]
            }
        }

        self.help_text = {
            0: "Commandes disponibles : suivant, quitter.",
            1: "Commandes disponibles : suivant, précédent, conversation, répondre, quitter.",
            2: "Commandes disponibles : suivant, précédent, lecture, quitter.",
            3: "Commandes disponibles : oui, non."
        }


    def get_command(self, type: int = 1) -> str:
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
        commands = self.commands.get(type, {})

        if not self.voice:
            # keyboard mode
            prompt = f"\n[Commande] {self.help_text[type]} → "
            cmd = input(prompt).lower().strip()
            return cmd if cmd in commands else ""
        else:
            # voice mode
            prompt = ""
            if self.help_activated :
                prompt = f"Vous pouvez dire : {self.help_text[type]}"
            cmd = self.voice_input(prompt=prompt)

            if "commande" in cmd or "aide" in cmd or "options" in cmd:
                cmd = self.voice_input(prompt=self.help_text[type])

            cmd_words = set(cmd.lower().split())
            for key, synonyms in commands.items():
                if cmd_words.intersection(set(s.lower() for s in synonyms)):
                    return key  
        return ""
    
    def keyboard_input(self, prompt="Votre saisie : "):
        return input(prompt).lower().strip()
    
    def voice_input(self, prompt="Parlez maintenant..."):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            if self.tts_instance:
                self.tts_instance.say(prompt)
            else:
                print(prompt)
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source)

        try:
            text = r.recognize_google(audio, language="fr-FR")
            if self.tts_instance:
                self.tts_instance.say(f"Vous avez dit : {text}")
            else:
                print(f"Vous avez dit : {text}")
            if text is not None:
                text=text.lower().strip()
            return text
        except sr.UnknownValueError:
            if self.tts_instance:
                self.tts_instance.say("Je n'ai pas compris ce que vous avez dit.")
            else:
                print("Je n'ai pas compris ce que vous avez dit.")
            return self.voice_input(prompt=prompt)
        except sr.RequestError as e:
            if self.tts_instance:
                self.tts_instance.say(f"Erreur avec le service de reconnaissance vocale : {e}")
            else:
                print(f"Erreur avec le service de reconnaissance vocale : {e}")
            raise e
        
    
    def input_and_validate(self, initial_prompt="Parlez maintenant ...",validation_prompt="validez vous ce texte ?", fallback_prompt="Texte invalide, veuillez réessayer", type=0):
        """
        Obtains input from the user (voice or keyboard) and validates it.

        Type 0 : Prefer voice input, fallback to keyboard if invalid.
        Type 1 : Voice input only, loops until valid.
        Type 2 : Keyboard input only, loops until valid.
        """
        
        while True:
            if type == 0:
                # Try voice first
                user_input = self.voice_input(prompt=initial_prompt)
            elif type == 1:
                # Voice only
                user_input = self.voice_input(prompt=initial_prompt)
            else:
                # Keyboard only
                user_input = self.keyboard_input(prompt=initial_prompt)

            # --- Validation step ---
            self.tts_instance.say(validation_prompt)
            cmd = self.get_command(type=3)

            if user_input and cmd == "y":
                return user_input

            self.tts_instance.say(fallback_prompt+ "\n")
            
            if type == 0:
                return self.keyboard_input(prompt=fallback_prompt+ "\n")

if __name__ == "__main__":
    tts_instance = TTS(preference="hortense")
    input_sys = InputSystem(tts_instance = tts_instance, voice=True, help_activated = False)
    
    input = input_sys.input_and_validate(type = 1)
    tts_instance.say(f"retour obtenu : {input}")

    # tts_instance.say("Bonjour, que voulez-vous me dire ?")
    # user_text = input_sys.voice_input(prompt="test")
    # tts_instance.say(f"retour obtenu : {user_text}")
