import datetime

def console_out(message, actor):
    print(f"{datetime.datetime.now().time()} : {actor} : {message}")