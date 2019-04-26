import datetime

def console_out(message, actor):
    print(f"{datetime.datetime.now().time()} : {actor} : {message}")

def console_out_exception(message, e, actor):
    template = "An exception of type {0} occurred. Arguments:{1!r}"
    ex_str = template.format(type(e).__name__, e.args)
    console_out(f"{message} Error: {ex_str}", actor)