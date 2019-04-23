import datetime

def console_out(message, actor):
    print(f"{datetime.datetime.now().time()} : {actor} : {message}")

def console_out_many(messages, actor):
    for message in messages:
        print(f"{datetime.datetime.now().time()} : {actor} : {message}")