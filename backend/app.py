import flask
from flask import request, jsonify, Response, stream_with_context
from GPT_API import ChatGPT, get_gpt3_answer
from flask_cors import CORS
import json

import os
import sys
import dotenv
import yaml
import ast

workdir = os.path.dirname(os.path.abspath(__file__))


def load_actions():
    print("Loading actions...")
    with open(os.path.join(workdir, "actions.yml"), "r") as f:
        actions = yaml.safe_load(f)
    return actions['actions']


actions = load_actions()
actions_str = ', \n'.join([f"'{action}' ({val['description']})" for action, val in actions.items()])


def detect_action_arguments_in_user_input(user_input, action):
    chat = ChatGPT(instruction="")
    action_names = list(actions.keys())
    action_names.remove("no_action")
    if action in action_names:
        action_dict = actions[action]
        prompt = f"""
[GENERAL CONTEXT] You are an machine that detects arguments required for a specific action intent.
[ACTION] {action}
[INSTRUCTION] {action_dict['instruction']}
[REQUIRED ARGUMENTS] {action} requires {len(action_dict['args'])} arguments: 
{', '.join([f"{arg} ({val['description']})" for arg, val in action_dict['args'].items()])}
[USER INPUT] {user_input}
[OUTPUT FORMAT] {action_dict['format']}
Output:
        """
        res = chat.get_chatgpt_answer(user_input, instruction=prompt, formal=True)
        try:
            parsed_res = ast.literal_eval(res)
        except Exception as e:
            logging.error(f"Could not parse output of GPT-3: {res}")
            correction_prompt = f"""
[Instruction] The output of the previous prompt was not in the correct format. Please correct it.
[Output] {res}
[Output Format] Example: {action_dict['format']}
Output:
"""
            res = chat.get_chatgpt_answer(user_input, instruction=correction_prompt, formal=True)
            parsed_res = ast.literal_eval(res)

    elif action == "no_action":
        res = "{}"

    else:
        raise ValueError(f"Action {action} not supported")

    return ast.literal_eval(res)


def map_user_input_to_actions(user_input):
    chat = ChatGPT(instruction="")
    prompt = f"""
[GENERAL CONTEXT] You are an knowledge graph interaction machine that detects the intent in the message of a user and maps it to a tool.
[INSTRUCTION] Your task is to identify, which tool to use for the task. 
[TOOLS] 
{actions_str}
[USER INPUT] {user_input}
[OUTPUT FORMAT] The output should be a string with the name of the functionality. E.g. "do_action"
Output:
"""

    intended_action = chat.get_chatgpt_answer(user_input, instruction=prompt, formal=True)

    return intended_action


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

Frage sie ob sie heute etwas unternommen hat und ob sie sich gut fühlt. Wenn sie sich nicht gut fühlt, dann motiviere sie dazu, etwas zu unternehmen. Das könnte zum Beispiel ein Spiel sein: 
Du als Assistent sollst nun mit dem USER “Wer bin ich?” spielen. Dafür denkst DU dir eine berühmte Persönlichkeit aus, die jeder durchschnittliche Mensch kennt. Der USER versucht durch Nachfragen herauszufinden, an wen du denkst. 

- Du darfst NUR mit Ja oder Nein antworten
- Du darfst deine Person während des Spiels nicht ändern
- Sobald ich den richtigen Namen sage, musst du zustimmen
- Gib dem USER einen Hinweis, wenn er das verlangt""")


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

    response = Response(stream_with_context(chat_stream(message)), content_type="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    return response



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

    # requested_action = get_gpt3_answer(
    #     f"""Which of the following actions does the user want to do {message}", ["Contact his children", "Go for a walk", "Tell a joke", "Play a game", "See images of his children", "None of the above"]""")
    # # print(f"""Suggested action for the user: {requested_action}""")
    # action = map_user_input_to_actions(message)
    # action_args = detect_action_arguments_in_user_input(message, action)
    # print(f"""Suggested action for the user: {action}""", flush=True)
    # print(f"""Suggested action arguments for the user: {action_args}""", flush=True)

    action = "no_action"
    answer = chat_bot.chat(message)
    return {"response": answer, "requested_action": action}


# @app.route('/api/change', methods=['GET'])


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
