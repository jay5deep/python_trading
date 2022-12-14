import logging
import requests
import time

# assuming now contains a timezone aware datetime
now = datetime.now()
tz = pytz.timezone('Asia/Kolkata')
ind_time=now
ind_time = now.astimezone(tz)
print(ind_time.now().strftime("%d%m%Y %H:%M:%S"))

start_time = ind_time.now().replace(hour=9, minute=18, second=1, microsecond=0)
end_time = ind_time.now().replace(hour=17, minute=29, second=1, microsecond=0)

baseURL = "https://api.telegram.org/bot<YOUR BOT TOKEN>/getUpdates?timeout=100"
url =  baseURL
offset = None

def get_last_update_id(updates):
    update_ids = []
    for update in updates["result"]:
        update_ids.append(int(update["update_id"]))
    return max(update_ids)

text="-"

while((start_time < ind_time.now()) and (end_time > ind_time.now())):
    if offset:
        url = baseURL + "&offset={}".format(offset)

    print("url=",url)

    resp = requests.get(url)
    updates = resp.json()
    if len(updates["result"]) > 0:
        offset = get_last_update_id(updates) + 1

    print("offset=",offset)

    for update in updates["result"]:
        try:
            text = update["message"]["text"]
            print(text)
        except Exception as e:
            print("exception=",e)

    if len(text)>0:

        # You can Put all required if else conditions as per your need.
        if(text.lower()=="help"):
            telegram_bot_sendtext("Enter below numbers !!\n\n1. Kite PL\n2. Exit NFO MIS\n3. Exit NFO NRML\n4. Exit CDS MIS\n5. Exit CDS NRML")
        elif(text.lower()=="1"):
            send_status("All")
        elif(text.lower()=="2"):
            close_all("NFO","MIS")
        elif(text.lower()=="3"):
            close_all("NFO","NRML")
        elif(text.lower()=="4"):
            close_all("CDS","MIS")
        elif(text.lower()=="5"):
            close_all("CDS","NRML")
        else:
            print("Wait for command...")
            text="-"

    time.sleep(5)
