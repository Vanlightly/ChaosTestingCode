#!/usr/bin/env python
import pulsar
import sys
import time
import subprocess

topic = sys.argv[1]
reader_timeout = int(sys.argv[2])

def get_proxy_ip():
    bash_command = "bash ../cluster/get-node-ip.sh proxy"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    ip = output.decode('ascii').replace('\n', '')
    return ip

proxy_ip = get_proxy_ip()
client = pulsar.Client(f"pulsar://{proxy_ip}:6650")
message_id = pulsar.MessageId.earliest
print(f"Earliest message id: {message_id} Latest message id {latest_message_id}")
reader = client.create_reader(f'persistent://vanlightly/cluster-1/ns1/{topic}', message_id)

# blocks until first message is read
msg = reader.read_next()
msg_id = msg.message_id()
current = int(msg.data())
received = 1

try:
    timeouts = 0
    while True:
        try:
            msg = reader.read_next(5000)
            current = int(msg.data())
            msg_id = msg.message_id()

            if msg_id == latest_message_id:
                break

            received += 1
            if received % 10000 == 0:
                print(f"Received: {received}")
            
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            if 'Pulsar error: TimeOut' in message:
                timeouts += 1
                if latest_message_id != pulsar.MessageId.latest:
                    print(f"New latest message id: {pulsar.MessageId.latest}")
                    latest_message_id = pulsar.MessageId.latest
                elif timeouts > 5:
                    print("Time elapsed")
                    break

except KeyboardInterrupt:
    print("Reader cancelled")
finally:
    client.close()
    print("")
    print("Results------------------------------")
    print(f"Received: {str(received)}")
    print(f"Last msg id consumed: {msg_id}")
    print(f"Last msg id in Pulsar: {pulsar.MessageId.latest}")
    print("-------------------------------------")
