# -*- coding: utf-8 -*-
"""
Created on Wed Sep 30 19:50:47 2020

@author: Jaydeep Patel

pip install gTTS

"""
import os
from gtts import gTTS
from kiteconnect import KiteConnect
import time

kite = KiteConnect(api_key="Put your API key here")

kite.set_access_token("Put your access token here")

print(kite.profile())

def tell_my_pos():
    live = kite.positions()
    live = live['net']
    net = int(sum(d['pnl'] for d in live))

    mytext = 'Current Net Profit/Loss is: '+ str(net)

    # Language in which you want to convert
    language = 'en'

    # Passing the text and language to the engine,
    # here we have marked slow=False. Which tells
    # the module that the converted audio should
    # have a high speed
    myobj = gTTS(text=mytext, lang=language, slow=False)

    # Saving the converted audio in a mp3 file named
    # welcome
    myobj.save("text_to_speech.mp3")

    # Playing the converted file
    os.system("mpg321 text_to_speech.mp3")

i=0
while(i<50):
    tell_my_pos()
    i=i+1
    time.sleep(180)
