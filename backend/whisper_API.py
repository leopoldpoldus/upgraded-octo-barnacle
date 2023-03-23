import os
import openai
import dotenv
# import API key from .env file
dotenv.load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


def transcribe(audio_file, language="en"):
    transcript = openai.Audio.transcribe("whisper-1", audio_file, language=language)
    return transcript['text']

