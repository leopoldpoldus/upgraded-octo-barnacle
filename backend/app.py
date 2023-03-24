import flask
from flask import request, jsonify, Response, stream_with_context
from GPT_API import ChatGPT, get_gpt3_answer
from flask_cors import CORS
import json

import os
import sys
import dotenv

workdir = os.path.dirname((os.path.abspath(__file__)))
sys.path.append(workdir)
dotenv.load_dotenv(os.path.join(workdir, '.env'))

app = flask.Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

host = os.getenv("AZURE_VM_HOST")
username = os.getenv("AZURE_VM_USERNAME")
password = os.getenv("AZURE_VM_PASSWORD")

chat_bot_eng = ChatGPT(instruction="""[GENERAL INSTRUCTION] You are a digital companion for a senior citizen. Your task is to have a lively conversation and to personally engage with the person you are talking to. Act like a human conversation partner.

The USER is called Fritz and is a 86 year old grandfather. He has two children, Susan and Mike and 3 grandchildren. He likes to go for a walk and watch the birds. 

TASK: Ask Fritz about his day and motivate him to take actions which might better mood. This could include calling his children and going for a walk!""")
chat_bot_de = ChatGPT(instruction="""[GENERAL INSTRUCTION] Du bist ein Digitaler Begleiter für eine Person im höheren Alter. Deine Aufgabe ist es, eine angeregte Konversation zu führen und auf deinen Gesprächspartner persönlich einzugehen und in ein Gespräch zu verwickeln.

Rosalinde ist eine 87 Jahre alte Frau, die sich geistig fit halten möchte! Motiviere sie dazu.
Du als Assistent sollst nun mit dem USER “Wer bin ich?” spielen. Dafür denkst DU dir eine berühmte Persönlichkeit aus, die jeder durchschnittliche Mensch kennt. Der USER versucht durch Nachfragen herauszufinden, an wen du denkst. 

- Du darfst NUR mit Ja oder Nein antworten
- Du darfst deine Person während des Spiels nicht ändern
- Sobald ich den richtigen Namen sage, musst du zustimmen
- Gib dem USER einen Hinweis, wenn er das verlangt""")


# db = VectorDatabase(milvus_host='172.187.227.106', milvus_port=19530, milvus_username=username, milvus_password=password)


# def save_message(message):
#     id = db.add_information(message, 'user')
#     with open(os.path.join(os.path.dirname(workdir), f'data/{id}.txt'), 'w') as f:
#         f.write(message)

def chat_stream(message):
    sentence = ""
    for response in chat_bot.chat(message):
        res = response['choices'][0]['delta']
        if "content" in res:
            res = res["content"]
            sentence += res
        if '.' in res or '?' in res or '!' in res:
            data = {"text": sentence}
            sentence = ""

            yield f"data: {json.dumps(data)}\n\n".encode('utf-8')


@app.route('/api/chatbot/stream', methods=['GET'])
def chat():
    if 'text' in request.args:
        message = request.args['text']
        print(message)
    else:
        return "Error: No message field provided. Please specify a message."

    # answer = chat_bot.chat(message)
    response = Response(stream_with_context(chat_stream(message)), content_type="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    return response
    # return {"response": answer}

@app.route('/api/chatbot', methods=['GET'])
def chatbot():
    if 'text' in request.args:
        message = request.args['text']
        language = request.args['language']

        print(message)
    else:
        return "Error: No message field provided. Please specify a message."

    # mood = detect_mood(message)
    # instruction = get_instruction_mood(mood)
    # save_message(message)

    if language == 'en':
        chat_bot = chat_bot_eng
    else:
        chat_bot = chat_bot_de

    requested_action = get_gpt3_answer(f"""Which of the following actions does the user want to do {message}", ["Contact his children", "Go for a walk", "Tell a joke", "Play a game", "See images of his children", "None of the above"]""")
    print(f"""Suggested action for the user: {requested_action}""")
    answer = chat_bot.chat(message, system_intermission=f"""Suggested action for the user: {requested_action}""")
    return {"response": answer, "requested_action": requested_action}

# @app.route('/api/change', methods=['GET'])


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
