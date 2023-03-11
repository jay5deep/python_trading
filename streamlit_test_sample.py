# -*- coding: utf-8 -*-
"""
Created on Wed Dec 28 22:40:54 2022

@author: Jaydeep
"""
import streamlit as st # web development
import numpy as np # np mean, np random
import pandas as pd # read csv, df manipulation
import time # to simulate a real time data, time loop
import plotly.express as px # interactive charts
import os
import datetime
import glob
import pytz
import calendar
from datetime import date
from random import randint

# assuming now contains a timezone aware datetime
now = datetime.datetime.now()
tz = pytz.timezone('Asia/Kolkata')
ind_time=now
ind_time = now.astimezone(tz)
print(ind_time.now().strftime("%Y-%m-%d %H:%M:%S"))

my_date = date.today()
weekday_name = calendar.day_name[my_date.weekday()]
print(weekday_name)

###############################################################################

st.set_page_config(
    page_title = 'Live Algo Trading Dashboard',
    page_icon = '✅',
    layout = 'wide'
)

# dashboard title
date_time = "Live Algo Trading Dashboard"
st.title(date_time)

# top-level filters
# job_filter = st.selectbox("Select the Job", pd.unique(df['job']))
# # dataframe filter
# df = df[df['job']==job_filter]

# creating a single-element container.
placeholder = st.empty()

# near real-time / live feed simulation
i=0
while True:
    i=i+1

    nifty = 18000+randint(0, 50)
    banknifty = 40500+randint(0, 120)
    finnifty = 18200+randint(0, 30)
    india_vix = 13.66+randint(0, 2)
    pnl = 12500+randint(0, 500)
    available_margin = 200000+randint(0, 525250)
    opening_balance = 75000+randint(0, 50000)
    live_balance = 100000+randint(0, 50000)
    used_margin = 1500000+randint(0, 50000)
    total_margin = 2100000+randint(0, 50000)

    prev_nifty = 17900+randint(0, 90)
    prev_banknifty = 40700+randint(0, 150)
    prev_finnifty = 18150+randint(0, 60)
    prev_india_vix = 13.2+randint(0, 2)
    prev_pnl = 25000+randint(0, 5000)
    prev_available_margin = 250000+randint(0, 50000)
    prev_opening_balance = 60000+randint(0, 50000)
    prev_live_balance = 50000+randint(0, 50000)
    prev_used_margin = 1800000+randint(0, 50000)
    prev_total_margin = 2050000+randint(0, 50000)

    utilized=round(((total_margin-available_margin)/total_margin)*100,2)

    pl_d = round(((pnl-prev_pnl)/prev_pnl)*100,2)

    start_time = ind_time.now().replace(hour=9, minute=1, second=59, microsecond=0)
    end_time = ind_time.now().replace(hour=15, minute=31, second=59, microsecond=0)
    
    weekly_pnl = round(25000+pnl)

    rr = round((weekly_pnl/total_margin)*100,2)

    with placeholder.container():
        # create three columns
        kpi1, kpi2, kpi3, kpi4, kpi5, kpi6, kpi7, kpi8 = st.columns(8)

        # fill in those three columns with respective metrics or KPIs
        kpi1.metric(label="NIFTY BANK", value=round(banknifty,2), delta= round(banknifty) - round(prev_banknifty))
        kpi2.metric(label="NIFTY 50", value= round(nifty,2), delta= round(nifty) - round(prev_nifty))
        kpi3.metric(label="NIFTY FIN SERVICE", value= round(finnifty,2), delta= round(finnifty) - round(prev_finnifty))
        kpi4.metric(label="INDIA VIX", value= round(india_vix,2), delta= str((round(india_vix) - round(prev_india_vix))*round(prev_india_vix)/100)+' %')
        kpi5.metric(label="PNL", value= '₹ '+str(pnl), delta= round(pnl) - round(prev_pnl))
        kpi6.metric(label="Weekly PNL", value= '₹ '+str(weekly_pnl), delta= str(rr)+" %")
        kpi7.metric(label="Available Margin", value= '₹ '+str(round(available_margin/100000,2))+'L', delta= str(utilized)+' % utilized')
        kpi8.metric(label="Live Balance", value= '₹ '+str(round(live_balance/100000,2))+'L', delta= str(live_balance-opening_balance))

        time.sleep(3)
