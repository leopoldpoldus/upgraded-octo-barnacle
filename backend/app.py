import flask
from flask import request, jsonify
from GPT_API import ChatGPT
from flask_cors import CORS

import os
import sys
import dotenv

workdir = os.path.dirname((os.path.abspath(__file__)))
sys.path.append(workdir)
dotenv.load_dotenv(os.path.join(workdir, '.env'))

from VectorDatabase import VectorDatabase

app = flask.Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

host = os.getenv("AZURE_VM_HOST")
username = os.getenv("AZURE_VM_USERNAME")
password = os.getenv("AZURE_VM_PASSWORD")

chat_bot = ChatGPT()
# db = VectorDatabase(milvus_host='172.187.227.106', milvus_port=19530, milvus_username=username, milvus_password=password)


# def save_message(message):
#     id = db.add_information(message, 'user')
#     with open(os.path.join(os.path.dirname(workdir), f'data/{id}.txt'), 'w') as f:
#         f.write(message)


@app.route('/api/chatbot', methods=['GET'])
def chat():
    if 'text' in request.args:
        message = request.args['text']
    else:
        return "Error: No message field provided. Please specify a message."

    # mood = detect_mood(message)
    # instruction = get_instruction_mood(mood)

    # save_message(message)

    answer = chat_bot.chat(message)
    return {"response": answer}


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
