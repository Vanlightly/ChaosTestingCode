#!/usr/bin/env python
import pulsar
import sys
import time
import subprocess
from datetime import datetime
import threading
from collections import defaultdict

chaos_action = sys.argv[1]
topic_prefix = sys.argv[2]
test_num = int(sys.argv[3])
count = int(sys.argv[4])
kill_mark = int(sys.argv[5])
config = sys.argv[6].split('-')
ensemble_size = config[0]
write_quorum = config[1]
ack_quorum = config[2]

def log(text, to_file=False):
    global output_file
    time_now = datetime.now().strftime('%H:%M:%S')
    print(text)
    if to_file:
        output_file.write(f"{time_now}: {text}\n")

def write_duplicate(line):
    global dupl_file
    dupl_file.write(line + '\n')

def write_out_of_order(line):
    global out_of_order_file
    out_of_order_file.write(line + '\n')

def get_proxy_ip():
    bash_command = "bash ../cluster/get-node-ip.sh proxy"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    ip = output.decode('ascii').replace('\n', '')
    return ip

def create_cluster(e, qw, qa):
    subprocess.call(["./setup-test-run.sh", e, qw, qa])

def kill_broker():
    global topic, chaos_action
    subprocess.call(["./execute-chaos.sh", chaos_action, topic])
    

def send_callback(res, msg):
    global messages_pos_acked, messages_neg_acked, send_count, ack_count, pos_ack_count, neg_ack_count, kill_mark, killed, topic
    ack_count += 1

    if str(res) == "Ok":
        pos_ack_count += 1
        value = int(msg.data())
        messages_pos_acked.add(value)
    else:
        neg_ack_count += 1
        value = int(msg.data())
        messages_neg_acked.add(value)

    if ack_count % 50000 == 0:
        log(f"Send count: {str(send_count)} Ack count: {str(ack_count)} Pos: {str(pos_ack_count)} Neg: {str(neg_ack_count)}")    

    if ack_count > kill_mark and killed == False:
        killed = True
        r = threading.Thread(target=kill_broker)
        r.start()
    
def produce(produer):
    global send_count, ack_count, pos_ack_count, neg_ack_count

    # send the first message synchronously, to ensure everything is running ok
    producer.send(str(send_count).encode('utf-8'))
    messages_pos_acked.add(send_count)
    send_count += 1
    ack_count += 1
    pos_ack_count += 1

    # send bulk of messages asynchronously in order to achieve high message rate
    while send_count < count-1:
        if send_count - ack_count >= 10000: # ensure we don't have more than 10k in flight at a time
            time.sleep(0.1)
        else: 
            producer.send_async(str(send_count).encode('utf-8'), send_callback)
            messages_sent[send_count] = list()
            send_count += 1       

    # send last message in order to block until acked
    # this way we ensure all messages are acked by the end of this function
    producer.send(str(send_count).encode('utf-8'))
    messages_pos_acked.add(send_count)
    send_count += 1
    ack_count += 1
    pos_ack_count += 1

def read(reader):
    global out_of_order, received_count, duplicate, messages_sent, test_run
    final_msg_id = pulsar.MessageId.latest
    msg = reader.read_next()
    current = int(msg.data())
    lastMsg = msg
    received_count = 1
    last = current
    messages_sent[last].append(msg.message_id())

    while lastMsg.message_id() != final_msg_id:
        try:
            msg = reader.read_next(10000)
            current = int(msg.data())
            messages_sent[current].append(msg.message_id())
                        
            received_count += 1
            if received_count % 50000 == 0:
                log(f"Received: {received_count}")
                            
            if last >= current:
                line = f"{test_run}|{lastMsg.message_id()}|{str(last)}|{msg.message_id()}|{current}"
                if len(messages_sent[current]) > 1:
                    duplicate += 1
                    write_duplicate(line)
                else:
                    out_of_order += 1
                    write_out_of_order(line)

            last = current
            lastMsg = msg
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            if 'Pulsar error: TimeOut' in message:
                break
    
    if lastMsg.message_id() != final_msg_id:
        log("Latest message reached")
    else:
        log(f"Latest message not reached. Last read: {lastMsg.message_id()}, latest in topic is: {final_msg_id}")


test_run = 1

# create log files
start_time = datetime.now().strftime('%Y%m%d_%H:%M:%S')
output_file_w = open(f"test-output/{topic_prefix}_output.txt", "w")
output_file_w.write(f"{start_time} Start test\n")
dupl_file_w = open(f"test-output/{topic_prefix}_duplicates.txt", "w")
dupl_file_w.write("run|last_msg_id|last_value|curr_msg_id|curr_value\n")
out_of_order_file_w = open(f"test-output/{topic_prefix}_out_of_order.txt", "w")
out_of_order_file_w.write("run|last_msg_id|last_value|curr_msg_id|curr_value\n")

output_file = open(f"test-output/{topic_prefix}_output.txt", "a")
out_of_order_file = open(f"test-output/{topic_prefix}_out_of_order.txt", "a")
dupl_file = open(f"test-output/{topic_prefix}_duplicates.txt", "a")

while test_run <= test_num:

    # prepare cluster phase ---------------
    topic = topic_prefix + "_" + str(test_run)
    create_cluster(ensemble_size, write_quorum, ack_quorum)

    # run test
    send_count = 0
    ack_count = 0
    pos_ack_count = 0
    neg_ack_count = 0
    killed = False

    log(f"", True)
    log(f"Test Run #{test_run} on topic {topic}  ------------", True)

    # - WRITE PHASE --------------------
    proxy_ip = get_proxy_ip()
    messages_sent = defaultdict(list)
    messages_pos_acked = set()
    messages_neg_acked = set()
    client = pulsar.Client(f'pulsar://{proxy_ip}:6650')
    producer = client.create_producer(f'persistent://vanlightly/cluster-1/ns1/{topic}',
                        block_if_queue_full=True,
                        batching_enabled=True,
                        batching_max_publish_delay_ms=10,
                        max_pending_messages=1000000, #avoid producer slowdown after broker fail-overs
                        properties={
                            "producer-name": "test-producer-name",
                            "producer-id": "test-producer-id"
                        })


    try:
        produce(producer)
    except KeyboardInterrupt:
        log("Producer cancelled")
        sys.exit(1)
    except Exception as ex:
        template = "An exception of type {0} occurred. Arguments:{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        log("The producer has failed!!!")
        log(message)
        sys.exit(1)
    finally:
        client.close()

    # - READ PHASE --------------------
    received_count = 0
    out_of_order = 0
    duplicate = 0
    message_id = pulsar.MessageId.earliest
    
    conn_attempts = 1

    while True:
        proxy_ip = get_proxy_ip()

        try:
            client = pulsar.Client(f'pulsar://{proxy_ip}:6650')
            reader = client.create_reader(f'persistent://vanlightly/cluster-1/ns1/{topic}', message_id)
            break
        except Exception:
            if conn_attempts > 3:
                log("Could not connect, aborting test run")
                sys.exit(1)
            else:
                log("Failed to connect, will retry")
        
            conn_attempts += 1

    try:
        read(reader)
    except KeyboardInterrupt:
        log("Reader cancelled")
        sys.exit(1)
    finally:
        client.close()

    not_received = 0
    received_no_ack = 0
    msgs_with_dups = 0
    for msg_val, msg_ids in messages_sent.items():
        if len(msg_ids) == 0 and msg_val in messages_pos_acked:
            not_received += 1
        elif len(msg_ids) == 1 and msg_val not in messages_pos_acked:
            received_no_ack += 1
        elif len(msg_ids) > 1:
            msgs_with_dups += 1

    log("Results --------------------------------------------", True)
    log(f"Final send count: {str(send_count)}", True)
    log(f"Final ack count: {str(ack_count)}", True)
    log(f"Final positive ack count: {str(pos_ack_count)}", True)
    log(f"Final negative ack count: {str(neg_ack_count)}", True)
    log(f"Messages received: {str(received_count)}", True)
    log(f"Acked messages missing: {str(not_received)}", True)
    log(f"Non-acked messages received: {str(received_no_ack)}", True)
    log(f"Out-of-order: {str(out_of_order)}", True)
    log(f"Duplicates: {msgs_with_dups}", True)
    log("----------------------------------------------------", True)

    test_run += 1


