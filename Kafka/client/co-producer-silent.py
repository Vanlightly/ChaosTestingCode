from confluent_kafka import Producer
import atexit
import sys
from time import sleep

acks_mode = sys.argv[3]
p = Producer({'bootstrap.servers': '172.17.0.3:9092,172.17.0.4:9093,172.17.0.5:9094',
    'message.send.max.retries': 0,
    #'batch.num.messages': 1000,
    'default.topic.config': { 'request.required.acks': acks_mode }})

def delivery_report(err, msg):
    """ Called once for each message produced to indicate delivery result.
        Triggered by poll() or flush(). """
    global success, fail, run_id

    if err:
        fail += 1
    else:
        success += 1

def printStats():
    global run_id
    global sent
    global success
    global fail
    print("Run ID: " + run_id + " Sent: " + str(sent) + " Delivered: " + str(success) + " Failed: " + str(fail))

run_id = sys.argv[5]
topic = sys.argv[4]
count = int(sys.argv[1]) + 1
wait_period = float(sys.argv[2])
success = 0
fail = 0
sent = 0
atexit.register(printStats)

for data in range(1, count):
    # Trigger any available delivery report callbacks from previous produce() calls
    p.poll(0)

    # Asynchronously produce a message, the delivery report callback
    # will be triggered from poll() above, or flush() below, when the message has
    # been successfully delivered or failed permanently.
    p.produce(topic, str(data).encode('utf-8'), callback=delivery_report)
    sent += 1
    if wait_period > 0.0:
        sleep(wait_period)

# Wait for any outstanding messages to be delivered and delivery report
# callbacks to be triggered.
p.flush()