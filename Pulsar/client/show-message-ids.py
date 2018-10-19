#!/usr/bin/env python
import pulsar
import sys
import time
import subprocess

topic = sys.argv[1]

bash_command = "bash ../cluster/find-last-bk-entry.sh pulsar1 xyz_3"
process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
output, error = process.communicate()
lac_line = output.decode('ascii').replace('\n', '')
lac = lac_line.split(":")[1].replace("\"", "").replace(",", "")
    
print(f"Last confirmed entry: {lac}")
