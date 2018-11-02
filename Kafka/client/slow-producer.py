from confluent_kafka import Producer
import atexit
import sys
from time import sleep
import json

last_leader = 0
last_offset = 0

def my_stats_callback(json_str):
    global last_leader
    data = json.loads(json_str)
    curr_leader = data["topics"]["test1"]["partitions"]["0"]["leader"]
    # for b in data["brokers"].values():
    #     print(b["name"] + ": " + b["state"])

    if curr_leader != last_leader:
        print("Current leader: " + str(curr_leader))
        last_leader = curr_leader

def delivery_report(err, msg):
    """ Called once for each message produced to indicate delivery result.
        Triggered by poll() or flush(). """
    global success, fail, last_offset

    offset = "none"
    if msg.offset():
        offset = str(msg.offset())
        if msg.offset() < last_offset:
            print("Partition fail-over, messages lost: " + str(last_offset - msg.offset()))
        last_offset = msg.offset()

    if err or msg.error():
        fail += 1
        print("ERROR! Value: " + msg.value().decode("utf-8") + " Offset: " + offset + " Error: " + err.str())
    else:
        success += 1
        
        print("Value: " + msg.value().decode("utf-8") + " Offset: " + offset)

    #if (success + fail) % 10000 == 0:
    #    print("Success: " + str(success) + " Failed: " + str(fail))

def printStats():
    global sent
    global success
    global fail
    print("Sent: " + str(sent))
    print("Delivered: " + str(success))
    print("Failed: " + str(fail))

acks_mode = sys.argv[3]
p = Producer({'bootstrap.servers': '172.17.0.3:9092,172.17.0.4:9093,172.17.0.5:9094',
    'message.send.max.retries': 0,
    #'batch.num.messages': 1000,
    #'stats_cb': my_stats_callback,
    #'statistics.interval.ms': 1000,
    'default.topic.config': { 'request.required.acks': acks_mode }})

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