from __future__ import unicode_literals

import json
import logging
import random

from flask import Flask
from flask import request

import dialogflow_v2
import os
import psycopg2

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

@app.route('/')
def index():
    return '<h1>MADE Marusya Skill</h1>'


@app.route('/marusya', methods=['POST'])
def postJsonHandler():
    logging.info(request.is_json)
    text = ''
    if request.json["session"]["new"]:
        text = 'Привет, я домашнее задание для MADE и пока ничего не умею'
    elif request.json["request"]["command"] == 'on_interrupt':
        text = 'Прощайте. Да прибудет с вами ... ох уж эти старые привычки'
    elif request.json['request']['command'] == 'debug':
        text = json.dumps(request.json)
    else: 
        text_input = dialogflow_v2.types.TextInput(text=request.json['request']['command'], language_code=dialogFlowSessionLanguage)
        query_input = dialogflow_v2.types.QueryInput(text = text_input)
        df_response = session_client.detect_intent(session_path, query_input)
        text =df_response.query_result.fulfillment_text


    response = {
        "version": request.json['version'],
        "session": request.json['session'],
        "response": {
            "end_session": False,
            "text": text,
            "debug": df_response.query_result
        }
    }
    logging.info(f"response: {response}")

    return json.dumps(response, ensure_ascii=False, indent=2)




forecasts_query_template = "select predictor, t1.DATE, t4.CLOSE, prediction_on, prediction, t41.close as actual_price,\
           case when prediction > t4.close then log((t41.close)/t4.close) else -log((t41.close)/t4.close) end as PnL\
    from\
    (\
    select timestamp::date as DATE, MIN(timestamp::time) as OPEN_TIME, MAX(timestamp::time) as CLOSE_TIME from allquotes\
    where TICKER ='%PLACEHOLDER%'\
    group by DATE) t1\
    inner join\
    (select timestamp::date as DATE, timestamp::time as TIME, CLOSE from allquotes\
    where TICKER ='%PLACEHOLDER%'\
    ) t4\
    on t1.CLOSE_TIME = t4.TIME and t1.DATE = t4.DATE\
    inner join\
    (select predictor, current_price, prediction_date, prediction_on, prediction from predictions\
    where ASSET ='%PLACEHOLDER%'\
    ) t2\
    on t1.DATE = t2.prediction_date\
    inner join\
    (select timestamp::date as DATE, timestamp::time as TIME, CLOSE from allquotes\
    where TICKER ='%PLACEHOLDER%'\
    ) t41\
    on t41.DATE = t2.prediction_on\
    inner join\
    (\
    select timestamp::date as DATE, MIN(timestamp::time) as OPEN_TIME, MAX(timestamp::time) as CLOSE_TIME from allquotes\
    where TICKER ='%PLACEHOLDER%'\
    group by DATE) t11\
    on t11.CLOSE_TIME = t41.TIME and t11.DATE = t41.DATE\
    order by t1.DATE desc"


def get_forecasts_model(ticker):
    conn = psycopg2.connect( 
        user=user, 
        password=password,
        host=host, 
        dbname=db)

    cursor = conn.cursor()

    query = forecasts_query_template.replace('%PLACEHOLDER%', ticker)
    my_list = []

    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchall()

    for row in result:
        my_list.append({
            "predictor": str(row[0]), 
            "forecast_date": str(row[1]), 
            "close": float(row[2]), 
            "predicted_on": str(row[3]), 
            "prediction": float(row[4]),
            "actual_price": float(row[5]),
            "pnl": float(row[6]),
            })

    return my_list   


if __name__ == '__main__':
    app.run(debug=True)