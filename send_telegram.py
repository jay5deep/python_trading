# -*- coding: utf-8 -*-
"""
Created on Mon Sep 28 18:43:57 2020

@author: Jaydeep Patel

https://medium.com/@xabaras/sending-a-message-to-a-telegram-channel-the-easy-way-eb0a0b32968

"""


import requests


def send_telegram(bot_message,bot_chatID):
    bot_token = 'put your bot_token'
    bot_chatID = bot_chatID
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
    response = requests.get(send_text)
    return response.json()

send_telegram("Pass your msg here","Pass your chat id here")