from tts import TTS
from voice import voice_input


class InputSystem:
    def __init__(self, tts_instance=None, voice=True):
        self.tts_instance = tts_instance # Instance of TTS class for voice feedback
        self.voice = voice # True for voice input, False for keyboard input
        self.commands = {
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

        self.help_text = {
            0: "Commandes disponibles : suivant, quitter.",
            1: "Commandes disponibles : suivant, précédent, message, quitter.",
            2: "Commandes disponibles : suivant, précédent, lecture, quitter."
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
            if self.tts_instance:
                self.tts_instance.say(f"Vous pouvez dire : {self.help_text[type]}")
            cmd = voice_input(prompt="Votre commande...").lower().strip()

            if "commande" in cmd or "aide" in cmd or "options" in cmd:
                if self.tts_instance:
                    self.tts_instance.say(self.help_text[type])
                cmd = voice_input(prompt="Votre commande...").lower().strip()

            cmd_words = set(cmd.lower().split())
            for key, synonyms in commands.items():
                if cmd_words.intersection(set(s.lower() for s in synonyms)):
                    return key  
        return ""
