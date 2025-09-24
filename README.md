# ai-mail-reader

Un agent intelligent en Python qui peut :
- Lire vos mails Gmail à voix haute,
- Chercher des mails par expéditeur, objet ou contenu,
- Lire le contenu d’un mail,
- Aider à rédiger et envoyer une réponse.

Le projet utilise :
- **Gmail API** pour accéder aux mails,
- **LLM** (modèle local ou API) comme cerveau,
- **TTS** (text-to-speech) pour lecture vocale,
- **Python** pour l’orchestration.

# Installation

## Cloner le projet

```bash
git clone https://github.com/ton-pseudo/ai-mail-reader.git
cd ai-mail-reader
```

## Créer un venv python et installer les dépendances
```bash
python -m venv .venv
source .venv/bin/activate  # Linux / Mac
.venv\Scripts\activate # Windows
pip install -r requirements.txt
```

## Activer Gmail API

Il faut récupérer les fichiers credentials.json et token.json

Étapes :

Rendez-vous sur [Google Cloud Console](https://console.cloud.google.com/).

Cliquez en haut sur Sélectionner un projet → Nouveau projet.
Donnez un nom, ex: ai-mail-reader.

Activez l’API Gmail :

Menu → API & Services → Bibliothèque

Cherchez Gmail API → Activer.

Créez des identifiants OAuth :

Menu → API & Services > Identifiants

Cliquez sur Créer identifiants > ID client OAuth 2.0

Type d’application : Application Bureau

Téléchargez le fichier credentials.json.

Placez credentials.json dans le dossier ./secrets/ de votre projet.

## Premier lancement

```bash
python gmail_client.py
```

La première fois :

Une fenêtre de navigateur s’ouvre pour vous demander d’autoriser l’application à accéder à votre Gmail.

Après validation, un fichier token.json est créé (il garde votre session).

Vous devriez voir la liste des expéditeurs et objets des 5 derniers mails non lus.

## Attention
Ne partagez jamais votre fichier credentials.json ou token.json.

## Stack utilisée

- Python 3.10+
- Gmail API (via google-api-python-client)
- TTS : pyttsx3
- LLM : modèles open source (Mistral) ou API (OpenAI)