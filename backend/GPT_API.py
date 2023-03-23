from time import sleep

import openai
import json
import os
import logging

logger = logging.getLogger(__name__)

working_dir = os.path.dirname(os.path.abspath(__file__))

import dotenv

# import API key from .env file
dotenv.load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


def get_gpt3_answer(prompt, model="text-davinci-003", temperature=1, max_tokens=2000, top_p=0.2,
                    frequency_penalty=0.0, presence_penalty=0.0):
    max_retry = 5
    retry = 0
    # print(prompt)

    prompt = prompt.encode(encoding='ASCII', errors='ignore').decode()
    while True:
        try:
            response = openai.Completion.create(
                engine=model,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty)

            text = response['choices'][0]['text'].strip()  # get the generated text
            logger.debug(f"Prompt: {prompt}\nGenerated text: {text}")
            return text

        except Exception as oops:
            retry += 1
            if retry >= max_retry:
                return f"GPT3 error: {oops}"
            logger.error('Error communicating with OpenAI:', oops)
            sleep(1)


class ChatGPT:
    def __init__(self, messages=None, instruction=None, model="gpt-3.5-turbo", temperature=1, max_tokens=2000, top_p=1,
                 frequency_penalty=0.0, presence_penalty=0.0,
                 stream=False):

        if instruction is None:
            instruction = "You are a problem solving bot that helps users to define and solve their problems."

        self.instruction = instruction
        self.instruction_message = {"role": "system", "content": instruction}

        if messages is None:
            self.messages = [self.instruction_message]
        else:
            self.messages = [self.instruction_message] + messages

        self.stream = stream
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty

        # summarize messages if they are too long
        self.reduce_message_buffer()

    def reduce_message_buffer(self):
        if len(self.messages) > 5:
            messages_to_summarize = self.messages[1:-2]
            summary = self.summarize_messages(messages_to_summarize)
            self.messages = [self.instruction_message] + \
                            [{"role": "system", "content": f"Summary of the previous conversation: \n {summary}"}] + \
                            self.messages[-2:]

    def summarize_messages(self, messages):
        conversation = ""
        for message in messages:
            conversation += message["role"] + ": " + message["content"]

        summary = self.get_chatgpt_answer(conversation,
                                          instruction="Summarize the conversation in short on concise bullet points.")
        print(summary)
        return summary

    def get_chatgpt_answer(self, message, message_history=None, instruction=None, formal=False,
                           system_intermission=None):
        if instruction is None:
            instruction = self.instruction_message
        else:
            instruction = {"role": "system", "content": instruction}

        if formal:
            temp = 0
        else:
            temp = self.temperature

        if message_history is None:
            message_history = [instruction]
        messages = message_history + [{"role": "user", "content": message}]

        if system_intermission is not None:
            messages.append({"role": "system", "content": system_intermission})

        max_retry = 5
        retry = 0
        # print(prompt)

        # prompt = prompt.encode(encoding='ASCII', errors='ignore').decode()
        while True:
            try:
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    temperature=temp,
                    max_tokens=self.max_tokens,
                    top_p=self.top_p,
                    frequency_penalty=self.frequency_penalty,
                    presence_penalty=self.presence_penalty,
                    stream=self.stream)

                if self.stream:
                    return response

                text = response['choices'][0]['message']["content"].strip()  # get the generated text
                messages_str = '\n'.join([f'{x["role"]}: {x["content"]}' for x in messages])
                logger.debug(f"Prompt:  {messages_str}\nGenerated text: {text}")
                return text

            except Exception as oops:
                retry += 1
                if retry >= max_retry:
                    return f"GPT3 error: {oops}"
                logger.error('Error communicating with OpenAI:', oops)
                sleep(1)

    def chat(self, message, instruction=None, additional_information=None, save_message=True, message_saver_fn=None,
             reduce_message_buffer=True, system_intermission=None):

        if instruction is not None:
            self.messages.append({"role": "system", "content": instruction})

        if additional_information is not None:
            self.messages.append({"role": "system", "content": f"Information: {additional_information}"})

        if save_message is True:
            self.messages.append({"role": "user", "content": message})
            if message_saver_fn is not None:
                message_saver_fn({"role": "user", "content": message})

        answer = self.get_chatgpt_answer(message, message_history=self.messages,
                                         system_intermission=system_intermission)
        if self.stream:
            return answer

        # remove the last message from the list
        if instruction is not None:
            self.messages.pop()

        if save_message is True:
            self.messages.append({"role": "assistant", "content": answer})
            if message_saver_fn is not None:
                message_saver_fn({"role": "assistant", "content": answer})

        if reduce_message_buffer:
            self.reduce_message_buffer()

        return answer

    def get_messages(self):
        return self.messages

    def add_message(self, message):
        self.messages.append(message)

    def change_instruction(self, instruction):
        self.instruction = instruction
        self.messages[0]["content"] = instruction

    def clear_messages(self):
        self.messages = [{"role": "system", "content": self.instruction}]


def get_embedding(text, model="text-embedding-ada-002"):
    text = text.replace("\n", " ")
    return openai.Embedding.create(input=[text], model=model)['data'][0]['embedding']


if __name__ == "__main__":
    chat = ChatGPT()
    while True:
        message = input("Enter message: ")
        answer = chat.chat(message)
