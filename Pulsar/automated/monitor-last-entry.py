#!/usr/bin/env python
import sys
import time
import subprocess

def get_last_confirmed_entry(broker, topic):
    bash_command = f"bash ../cluster/find-last-bk-entry.sh {broker} {topic}"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    lac_line = output.decode('ascii').replace('\n', '')
    return lac_line

broker = sys.argv[1]
topic = sys.argv[2]

while True:
    last_entry = get_last_confirmed_entry(broker, topic)
    print(last_entry)