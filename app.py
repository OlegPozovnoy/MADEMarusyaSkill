from __future__ import unicode_literals

import json
import logging
import random

from flask import Flask
from flask import request

app = Flask(__name__)

@app.route('/')
def index():
    return '<h1>MADE Marusya Skill</h1>'


@app.route('/marusya', methods=['POST'])
def postJsonHandler():
    logging.info(request.is_json)
    content = request.get_json()
    command = content['request']['command'].lower().split()
    logging.info(f'\ncommand: {command}')
    card = {}
    buttons = []
    text = ''
    image_array = [457239017,457239018,457239019]
    if request.json["session"]["new"]:
        text = 'Привет, я домашнее задание для MADE и пока ничего не умею'
    elif request.json["request"]["command"] == 'on_interrupt':
        text = 'Прощайте. Да прибудет с вами ... ох уж эти старые привычки'
    elif "привет" in command:
        text = "Привет!"
    elif "картинка" in command:
        text = "Вот вам картинка!"
        card = {
            "type": 'BigImage',
            "image_id": random.choice(image_array)
        }
    elif "карусель" in command:
        text = "Вот вам карусель!"
        card = {
            "type": 'ItemsList',
            "items": [{"image_id": x} for x in image_array]
        }
    elif "кнопки" in command:
        text = "Вот вам кнопки: кто же GOAT в теннисе?"
        buttons = [{"title": "Джокович"},{"title": "Надаль"},{"title": "Федерер"}]
    else:
        text = "Шпрехен зе дойч-хендехох! Нихт понимать!"

    response = {
        "version": request.json['version'],
        "session": request.json['session'],
        "response": {
            "end_session": False,
            "text": text,
            "card": card,
            "buttons": buttons
        }
    }
    logging.info(f"response: {response}")
    return json.dumps(response, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    app.run(debug=True)