import flask
from flask import request, jsonify
from GPT_API import ChatGPT
from flask_cors import CORS

app = flask.Flask(__name__)
CORS(app)

chat_bot = ChatGPT()


@app.route('/api/chatbot', methods=['GET'])
def chat():
    if 'text' in request.args:
        message = request.args['text']
    else:
        return "Error: No message field provided. Please specify a message."

    answer = chat_bot.chat(message)
    return {"response": answer}
