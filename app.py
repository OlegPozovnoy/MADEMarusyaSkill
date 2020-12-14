from __future__ import unicode_literals

import json
import logging
import random
from google_trans_new import google_translator  

from flask import Flask
from flask import request

import dialogflow_v2
import os
import psycopg2
import requests
from time import sleep
from fuzzywuzzy import fuzz

app = Flask(__name__)


sessionStorage = {}

googleProjectID =  os.environ['GOOGLE_PROJECT_ID']
dialogFlowSessionID = os.environ['DIALOG_FLOW_SESSION_ID']
dialogFlowSessionLanguage =  os.environ['DIALOG_FLOW_LANGUAGE_CODE']

session_client = dialogflow_v2.SessionsClient()
session_path = session_client.session_path(googleProjectID, dialogFlowSessionID)

# db connection
user = os.environ['POSTGRES_USER']
password = os.environ['POSTGRES_PASSWORD']
host = os.environ['POSTGRES_HOST']
db = os.environ['POSTGRES_DATABASE']

weather_api = os.environ['WEATHER_API']

@app.route('/')
def index():
    return '<h1>MADE Marusya Skill</h1>'


@app.route('/marusya', methods=['POST'])
def postJsonHandler():
    logging.info(request.is_json)
    text = ''
    uid = request.json["session"]['user_id']
    if request.json["session"]["new"]:
        text = 'Привет, я ваш ассистент. Я могу рассказать про погоду ["какая погода в ..."], добавлять задания в список дел ["добавь в список дел"],\
             удалять задания из списка["удали задание"], переводить предложения на английский["переведи фразу"]. Также вы можете пообщаться с прошлой версией Пивбота.["Вызови Пивбота"]'
    elif request.json["request"]["command"] == 'on_interrupt':
        text = 'До свидания.'
    elif request.json['request']['command'] == 'debug':
        text = json.dumps(request.json)
    else: 
        text_input = dialogflow_v2.types.TextInput(text=request.json['request']['command'], language_code=dialogFlowSessionLanguage)
        query_input = dialogflow_v2.types.QueryInput(text = text_input)
        df_response = session_client.detect_intent(session_path, query_input)
        print("df_response",df_response)    
        #print("output_contexts", df_response.query_result.output_contexts[0])    
        text =df_response.query_result.fulfillment_text
        if df_response.query_result.intent.display_name == "get_weather" and df_response.query_result.all_required_params_present:
            print(df_response.query_result.parameters)
            result = make_weather_api_call(str(df_response.query_result.parameters.fields['geo-city'].string_value))
            text += str(result)
        elif df_response.query_result.intent.display_name == "get_translation - fallback":
            print("translatign", df_response.query_result.query_text)   
            translator = google_translator()  
            translate_text = translator.translate(df_response.query_result.query_text,lang_tgt='en')  
            text += str(translate_text)
        elif df_response.query_result.intent.display_name == "get_my_tasks":
            print("get_my_tasks", uid)
            tasks = get_task(uid)
            if len(tasks) == 0:
                text += str("Пока у вас ничего не запланировано")
            else:
                text += "\n".join(tasks)  
        elif df_response.query_result.intent.display_name == "create_task - fallback":
            print("create_task - fallback", uid, df_response.query_result.query_text)
            insert_task(uid, df_response.query_result.query_text)            
        elif df_response.query_result.intent.display_name == "delete_task - fallback":
            print("delete_task - fallback", uid, df_response.query_result.query_text)
            current_task = df_response.query_result.query_text
            task_list = get_task(uid)
            deleted_tasks = []
            for task in task_list:
                if fuzz.ratio(task, current_task) > 0.85:
                    delete_task(uid, task)
                    deleted_tasks.append(task)
            
            if len(deleted_tasks) == 0:
                text = "Не могу найти в списке дел " + str(current_task)
            else:
                text += "\n".join(deleted_tasks)

            insert_task(uid, df_response.query_result.query_text)   

    response = {
        "version": request.json['version'],
        "session": request.json['session'],
        "response": {
            "end_session": False,
            "text": text
        }
    }
    logging.info(f"response: {response}")

    return json.dumps(response, ensure_ascii=False, indent=2)




query_insert = "insert into marusya (uid, task_name) values ('%uid%', '%task_name%')"
query_select = "select task_name from marusya where uid = '%uid%'"
query_delete = "delete from marusya where uid = '%uid%' and task_name='%task_name%'"

def make_weather_api_call(city):
    print("api call", city)
    url = 'http://api.openweathermap.org/data/2.5/weather?q='+str(city)+',ru&APPID=' + str(weather_api)
    result = requests.get(url)
    print(result.json())
    return result.json()



def insert_task(uid, task_text):
    conn = psycopg2.connect( 
        user=user, 
        password=password,
        host=host, 
        dbname=db)
    conn.autocommit = True

    print("insert_task", uid, task_text)
    query = query_insert.replace('%uid%', uid)
    query = query.replace('%task_name%', task_text)
    print("query", query)
    cursor = conn.cursor()
    cursor.execute(query)
    #sleep(0.05)
    return 

def get_task(uid):
    conn = psycopg2.connect( 
        user=user, 
        password=password,
        host=host, 
        dbname=db)
    conn.autocommit = True

    query = query_select.replace('%uid%', uid)
    print("query")
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchall()
    my_list = []

    for row in result:
        my_list.append( str(row[0]))

    return my_list   


def delete_task(uid, task_text):
    conn = psycopg2.connect( 
        user=user, 
        password=password,
        host=host, 
        dbname=db)
    conn.autocommit = True

    print("delete_task", uid, task_text)
    query = query_delete.replace('%uid%', uid)
    query = query.replace('%task_name%', task_text)
    print("query", query)
    cursor = conn.cursor()
    cursor.execute(query)
    #sleep(0.05)
    return 

if __name__ == '__main__':
    app.run(debug=True)