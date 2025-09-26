import speech_recognition as sr
from tts import TTS

def voice_input(prompt="Parlez maintenant..."):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print(prompt)
        r.adjust_for_ambient_noise(source, duration=0.5)
        audio = r.listen(source)

    try:
        text = r.recognize_google(audio, language="fr-FR")
        print(f"Vous avez dit : {text}")
        return text
    except sr.UnknownValueError:
        print("Je n'ai pas compris ce que vous avez dit.")
    except sr.RequestError as e:
        print(f"Erreur avec le service de reconnaissance vocale : {e}")

    return ""


if __name__ == "__main__":
    TTS_instance = TTS(preference="hortense")
    TTS_instance.say("Bonjour, que voulez-vous me dire ?")
    user_text = voice_input()
    TTS_instance.say(f"Vous avez dit : {user_text}")