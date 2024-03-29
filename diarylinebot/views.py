from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Diary
import json, os
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextSendMessage
import googletrans
import psycopg2
from datetime import datetime, date
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from pyChatGPT import ChatGPT
import matplotlib.pyplot as plt
import pyimgur
import matplotlib.dates as mdates
import pandas as pd
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    LocationSendMessage, ImageSendMessage, StickerSendMessage,
    VideoSendMessage, TemplateSendMessage, ButtonsTemplate, PostbackAction, MessageAction, URIAction,
    PostbackEvent, ConfirmTemplate, CarouselTemplate, CarouselColumn,
    ImageCarouselTemplate, ImageCarouselColumn, FlexSendMessage)

session_token = ''
key = ""
endpoint = ""
status_dict = {}
def authenticate_client():
    ta_credential = AzureKeyCredential(key)
    text_analytics_client = TextAnalyticsClient(
            endpoint=endpoint, 
            credential=ta_credential)
    return text_analytics_client

client = authenticate_client()
translator = googletrans.Translator()
connection = psycopg2.connect(user="postgres",\
    password="a96534200",\
    host="127.0.0.1",\
    port="5432",\
    database="Diary")
line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)
diary_id = 999999
modify_detail = {}
@csrf_exempt
def callback(request):

    if request.method == 'POST':
        signature = request.META['HTTP_X_LINE_SIGNATURE']
        body = request.body.decode('utf-8')
 
        try:
            events = parser.parse(body, signature)  # 傳入的事件
        except InvalidSignatureError:
            return HttpResponseForbidden()
        except LineBotApiError:
            return HttpResponseBadRequest()

        try:
            connection = psycopg2.connect(user="postgres",\
                    password="a96534200",\
                    host="127.0.0.1",\
                    port="5432",\
                    database="Diary")
            cursor = connection.cursor()

            for event in events:
                if isinstance(event, MessageEvent):
                    u_id = str(event.source.user_id)


                    global status_dict
                    global diary_id
                    if u_id not in status_dict:
                        status_dict[u_id] = 0
                    print(status_dict)

                    if status_dict[u_id] == 1:
                        api1 = ChatGPT(session_token)  # auth with session token
                        now = date.today()
                        date_t = datetime.strftime(now,'%Y-%m-%d')
                        content_c = event.message.text
                        results = translator.translate(content_c, dest='en').text
                        score_s = sentiment_analysis_example(client, results)
                        resp = api1.send_message(content_c)
                        postgres_insert_query = """ INSERT INTO diarylinebot_diary (user_id, content, date, score, response) VALUES (%s,%s,%s,%s,%s)"""
                        record_to_insert = (u_id, content_c, date_t, score_s, resp['message'])
                        cursor.execute(postgres_insert_query, record_to_insert)
                        connection.commit()
                        count = cursor.rowcount
                        print(count, "Record inserted successfully into mobile table")
                        content = TextSendMessage(text=resp['message'])
                        line_bot_api.reply_message(event.reply_token, content)
                        status_dict[u_id] = 0
                        api1.reset_conversation()  # reset the conversation
                        api1.close()  # close the session

                    elif status_dict[u_id] == 2:
                        confirm_template_message = TemplateSendMessage(
                            alt_text='Confirm template',
                            template=ConfirmTemplate(
                                text='確定修改?',
                                actions=[
                                    PostbackAction(
                                        label='確定修改',
                                        data='modify_yes'
                                    ),
                                    PostbackAction(
                                        label='不要修改',
                                        data='modify_no'
                                    )
                                ]
                            )
                        )
                        line_bot_api.reply_message(event.reply_token, confirm_template_message)
                        status_dict[u_id] = 0
                        modify_detail['content_c'] = event.message.text

                    else:
                        json_path = os.path.join(os.path.split(__file__)[0], 'button_template.txt')
                        with open(json_path, 'r', encoding='UTF-8') as f:
                            flexmessagestring = f.read()
                        flexmessagedict = json.loads(flexmessagestring)
                        flex_message = FlexSendMessage(alt_text='hello',contents=flexmessagedict)
                        line_bot_api.reply_message(event.reply_token, flex_message)

                elif isinstance(event, PostbackEvent):
                    u_id = str(event.source.user_id)
                    print(event.postback.data)

                    if event.postback.data == '寫日記':
                        content = TextSendMessage(text='可以開始寫日記了!')
                        line_bot_api.reply_message(event.reply_token, content)
                        status_dict[u_id] = 1

                    elif event.postback.data == 'analysis':
                        postgres_insert_query = """ SELECT date, score FROM diarylinebot_diary WHERE user_id = (%s) ORDER BY date DESC"""
                        record_to_insert = (u_id,)
                        cursor.execute(postgres_insert_query, record_to_insert)   
                        data = cursor.fetchall()
                        x_axis = []
                        y_axis = []
                        for i in range(len(data)):
                            x_axis.append(datetime.strftime(data[i][0],'%Y-%m-%d'))
                            y_axis.append(data[i][1])
                        print(x_axis)

                        

                        x_axis = pd.to_datetime(x_axis)
                        print(x_axis)
                        DF = pd.DataFrame()
                        DF['value'] = y_axis
                        DF = DF.set_index(x_axis)
                        plt.plot(DF)
                        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d')) 
                        plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1)) #設定x軸主刻度間距

                        plt.savefig('foo.png')
                        plt.close()
                        CLIENT_ID = '4c97c8ac6ec04bf'
                        PATH = "foo.png"
                        im = pyimgur.Imgur(CLIENT_ID)
                        uploaded_image = im.upload_image(PATH, title="score_image")
                        line_bot_api.reply_message(event.reply_token, ImageSendMessage(original_content_url = uploaded_image.link, 
                                                                    preview_image_url='https://i.imgur.com/9QSrfpV.png'))

                    elif event.postback.data == 'research':

                        json_path = os.path.join(os.path.split(__file__)[0], 'json.txt')
                        with open(json_path, 'r', encoding='UTF-8') as f:
                            flexmessagestring = f.read()
                        
                        # postgres_insert_query = """ SELECT content, date, score, response FROM diarylinebot_diary WHERE user_id = (%s)"""
                        postgres_insert_query = """ SELECT content, date, score, response FROM diarylinebot_diary WHERE user_id = (%s) ORDER BY date DESC"""
                        record_to_insert = (u_id,)
                        cursor.execute(postgres_insert_query, record_to_insert)   
                        data = cursor.fetchall()
                        flexmessagedict = json.loads(flexmessagestring)
                        for i in range(len(data)):
                            print('-'*20)
                            print(data)
                            date_display = datetime.strftime(data[i][1],'%Y-%m-%d')
                            flexmessagedict['contents'][i]['header']['contents'][0]['contents'][0]['text'] = date_display
                            score_display = str(round(data[i][2],2)*100) + '%'
                            flexmessagedict['contents'][i]['header']['contents'][1]['contents'][1]['text'] = score_display
                            flexmessagedict['contents'][i]['header']['contents'][2]['contents'][0]['width'] = score_display
                            flexmessagedict['contents'][i]['body']['contents'][0]['contents'][0]['contents'][1]['text'] = data[i][0]
                            flexmessagedict['contents'][i]['body']['contents'][0]['contents'][2]['contents'][1]['text'] = data[i][3]
                            if data[i][2]>=0.8:
                              flexmessagedict['contents'][i]['header']['backgroundColor'] = "#FF8888" #紅
                              flexmessagedict['contents'][i]['header']['contents'][0]['contents'][1]['url'] = "https://i.imgur.com/TSOCcuF.png"
                            elif data[i][2]>=0.6:
                              flexmessagedict['contents'][i]['header']['backgroundColor'] = "#FFBB66" #橙
                              flexmessagedict['contents'][i]['header']['contents'][0]['contents'][1]['url'] = "https://i.imgur.com/mJETuo1.png"
                            elif data[i][2]>=0.4:
                              flexmessagedict['contents'][i]['header']['backgroundColor'] = "#77DDFF" #藍
                              flexmessagedict['contents'][i]['header']['contents'][0]['contents'][1]['url'] = "https://i.imgur.com/tFrAsck.png"
                            elif data[i][2]>=0.2:
                              flexmessagedict['contents'][i]['header']['backgroundColor'] = "#99BBFF" #紫
                              flexmessagedict['contents'][i]['header']['contents'][0]['contents'][1]['url'] = "https://i.imgur.com/EUGnAvs.png"
                            elif data[i][2]>=0.0:
                              flexmessagedict['contents'][i]['header']['backgroundColor'] = "#9999FF" #more紫
                              flexmessagedict['contents'][i]['header']['contents'][0]['contents'][1]['url'] = "https://i.imgur.com/32TGKwm.png"
                        flex_message = FlexSendMessage(
                            alt_text='hello',
                            contents=flexmessagedict
                        )
                        line_bot_api.reply_message(event.reply_token, flex_message)

                    elif event.postback.data =='delete_yes':
                        postgres_insert_query = """ DELETE FROM diarylinebot_diary WHERE id=%s """
                        record_to_insert = (diary_id,)
                        cursor.execute(postgres_insert_query, record_to_insert)
                        connection.commit()
                        content = TextSendMessage(text='刪除成功')
                        line_bot_api.reply_message(event.reply_token, content)
                        count = cursor.rowcount
                        print(count, "Record Remove successfully into mobile table")

                    elif event.postback.data =='delete_no':
                        print("")

                    elif event.postback.data =='modify_yes':
                        api1 = ChatGPT(session_token)  # auth with session token
                        content_c = modify_detail['content_c']
                        results = translator.translate(content_c, dest='en').text
                        score_s = sentiment_analysis_example(client, results)
                        print(content_c)
                        resp = api1.send_message(content_c)
                        print("successfully!")
                        api1.reset_conversation()  # reset the conversation
                        api1.close()  # close the session
                        modify_detail['response'] = resp['message']
                        modify_detail['score_s'] = score_s
                        postgres_insert_query = """ UPDATE diarylinebot_diary SET content=%s , score=%s, response=%s WHERE id=%s"""
                        record_to_insert = (content_c, modify_detail['score_s'], modify_detail['response'], diary_id)
                        cursor.execute(postgres_insert_query, record_to_insert)
                        connection.commit()
                        count = cursor.rowcount
                        print(count, "Record Update successfully into mobile table")
                        content = TextSendMessage(text=modify_detail['response'])
                        line_bot_api.reply_message(event.reply_token, content)

                    elif event.postback.data =='modify_no':
                        status_dict[u_id] = 0

                    elif 'update' in event.postback.data:
                        modify_order = int(event.postback.data[6:])
                        postgres_insert_query = """ SELECT id, content, date, score, response FROM diarylinebot_diary WHERE user_id = %s ORDER BY date DESC """
                        record_to_insert = (u_id,)
                        cursor.execute(postgres_insert_query, record_to_insert)
                        data = cursor.fetchall()
                        diary_id = data[modify_order][0]
                        content = TextSendMessage(text='你想修改的日記內容如下(建議拷貝)\n'+data[modify_order][1])
                        line_bot_api.reply_message(event.reply_token, content)
                        status_dict[u_id] = 2

                    elif 'delete' in event.postback.data:
                        modify_order = int(event.postback.data[6:])
                        postgres_insert_query = """ SELECT id, content, date, score, response FROM diarylinebot_diary WHERE user_id = (%s) ORDER BY id ASC """
                        record_to_insert = (u_id,)
                        cursor.execute(postgres_insert_query, record_to_insert)   
                        data = cursor.fetchall()
                        diary_id = data[modify_order][0]
                        confirm_template_message = TemplateSendMessage(
                            alt_text='Confirm template',
                            template=ConfirmTemplate(
                                text='你確定要刪除'+data[modify_order][1],
                                actions=[
                                    PostbackAction(
                                        label='確定刪除',
                                        data='delete_yes'
                                    ),
                                    PostbackAction(
                                        label='不要刪除',
                                        data='delete_no'
                                    )
                                ]
                            )
                        )
                        line_bot_api.reply_message(event.reply_token, confirm_template_message)

        except (Exception, psycopg2.Error) as error:
            print("Failed to insert record into mobile table", error)

        finally:
            # closing database connection.
            if connection:
                cursor.close()
                connection.close()
                print("PostgreSQL connection is closed")
        return HttpResponse()
    else:
        return HttpResponseBadRequest()

def sentiment_analysis_example(client, content):

    documents = [content]
    response = client.analyze_sentiment(documents=documents)[0]
    return response.confidence_scores.positive

def sample_extractive_summarization(client, content):
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.textanalytics import (
        TextAnalyticsClient,
        ExtractSummaryAction
    ) 

    poller = client.begin_analyze_actions(
        [content],
        actions=[
            ExtractSummaryAction(max_sentence_count=4)
        ],
    )

    document_results = poller.result()
    for result in document_results:
        extract_summary_result = result[0]  # first document, first result
        if extract_summary_result.is_error:
            response = "...Is an error with code '{}' and message '{}'".format(extract_summary_result.code, extract_summary_result.message)
            return response
        else:
            response = " ".join([sentence.text for sentence in extract_summary_result.sentences])
            return response



# Diff: json can only store 12 items

# Work
# 1. PPT(Include Question、Motivation、Purpose, ways of presenting)
# 2. Google site
# 3. 
# CRUD
# plot score
# json style
# Button replacement 
# 4. Send Message to Parents
# 5. Azure
# 6. Xmind
# 7. Discussion Make
# 8. ChatGPT

# Tool
# Django
# PostgreSQL
# Azure
# Linebot Developer

# https://www.youtube.com/watch?v=sewBZGz5iJE
# https://www.youtube.com/watch?v=NrpnYQDQ5s4

# 流程
# 寫日記(C)
# 查看日記(RUD)
# 
# Ques
# Use training?
