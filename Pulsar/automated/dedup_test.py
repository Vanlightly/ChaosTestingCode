#!/usr/bin/env python
import pulsar
import sys
import time
import subprocess
from datetime import datetime
import threading
from collections import defaultdict
import re
from gather_info_functions import *

def log(text, to_file=False):
    global output_file
    print(text)
    if to_file:
        output_file.write(f"{text}\n")

def log_order(text):
    global order_file
    time_now = datetime.now().strftime('%H:%M:%S')
    print(text)
    order_file.write(f"{time_now}: {text}\n")

def create_cluster(e, qw, qa, dedup_enabled, slow):
    subprocess.call(["./setup-test-dedup-run.sh", e, qw, qa, dedup_enabled, slow])

def get_entry(msg_id):
    id = str(msg_id)    .replace("(", "").replace(")", "").split(",")
    first = int(id[0])
    entry = int(id[1])
    return [first, entry]

def is_same_entry(last_entry, current_entry):
    return last_entry[0] == current_entry[0] and last_entry[1] == current_entry[1]

def find_network_interface(ip_range):
    bash_command = f"bash ../cluster/find-interface-name.sh {ip_range}"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    return output.decode('ascii').replace('\n', '')

def kill_tcp_connections():
    ip = get_proxy_ip()
    ip_range = ip[0:ip.rfind('.')]
    network_iface = find_network_interface(ip_range)
    cmd = f"sudo timeout 10s sudo tcpkill -i {network_iface} -9 port 6650"
    subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)

def get_isolate_from_zk_partitions(target_node, topic):
    partition1 = list()
    partition2 = list()

    for node in get_live_nodes():
        if node != "zk1":
            partition1.append(node)

    for node in get_live_nodes():
        if node != target_node:
            partition2.append(node)

    partition1_arg = ",".join(partition1)
    partition2_arg = ",".join(partition2)

    return [target_node, partition1_arg, partition2_arg]

def kill_topic_owner():
    global topic, owner
    owner = get_topic_owner(topic)
    subprocess.call(["./execute-chaos.sh", "kill-specific-node", owner])

def isolate_topic_owner():
    global topic, partitions
    subprocess.call(["./execute-chaos.sh", "isolate-broker-from-zk", topic, partitions[0], partitions[1], partitions[2]])

def resolve_partition():
    subprocess.call(["./execute-chaos.sh", "resolve-partitions"])

def start_downed_broker():
    global owner
    subprocess.call(["./execute-chaos.sh", "start-specific-node", owner])

def send_callback(res, msg):
    global messages_pos_acked, messages_neg_acked, send_count, ack_count, pos_ack_count, neg_ack_count, action_mark, action_performed, topic, test_type
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

    if ack_count > action_mark and action_performed == False:
        action_performed = True

        if test_type == "kill-topic-owner":
            print(f"Preparing to kill topic owner: {topic}")
            r = threading.Thread(target=kill_topic_owner)
            r.start()
        elif test_type == "isolate-topic-owner":
            print(f"Preparing to isolate topic owner: {topic}")
            r = threading.Thread(target=isolate_topic_owner)
            r.start()
        elif test_type == "kill-tcp":
            print(f"Preparing to kill TCP connections: {topic}")
            r = threading.Thread(target=kill_tcp_connections)
            r.start()
        else:
            print(f"Chaos action not recognized!")
    
def produce(producer):
    global send_count, ack_count, pos_ack_count, neg_ack_count, messages_sent, messages_pos_acked, partitions, owner

    # send the first message synchronously, to ensure everything is running ok
    producer.send(str(send_count).encode('utf-8'))
    messages_pos_acked.add(send_count)
    send_count += 1
    ack_count += 1
    pos_ack_count += 1

    owner = get_owner_broker(topic)
    partitions = get_isolate_from_zk_partitions(owner, topic)

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
    log(f"Send count: {str(send_count)} Ack count: {str(ack_count)} Pos: {str(pos_ack_count)} Neg: {str(neg_ack_count)}")    

def read(reader):
    global received_count, messages_sent, topic, duplicate_jump_forward, duplicate_jump_back, jump_forward, jump_back
    last_confirmed = get_last_confirmed_entry(topic)
    log(f"Last confirmed entry: {last_confirmed}")

    msg = reader.read_next()
    msg_id = msg.message_id()
    msg_entry = get_entry(msg_id)
    current_payload = int(msg.data())
    received_count = 1
    messages_sent[current_payload].append(msg_id)
    reader_timeout = 10000
    last_payload = 0

    log(f"Start reading from {msg_id}")

    while True:
        try:
            msg = reader.read_next(reader_timeout)
            received_count += 1
            msg_id = msg.message_id()
            msg_entry = get_entry(msg_id)

            # lower the wait time towards the end
            if is_same_entry(last_confirmed, msg_entry):
                reader_timeout = 10000
            else:
                reader_timeout = 60000
            
            current_payload = int(msg.data())
            seen = len(messages_sent[current_payload]) > 0

            if seen:
                if last_payload >= current_payload:
                    duplicate_jump_back += 1
                    jump = str(last_payload - current_payload)
                    log_order(f"Test run: {test_run} DUPLICATE BLOCK - JUMP BACKWARDS {jump} ({str(last_payload)} -> {str(current_payload)})")
                elif last_payload + 1 < current_payload:
                    duplicate_jump_forward += 1
                    jump = str(current_payload - last_payload)
                    log_order(f"Test run: {test_run} DUPLICATE BLOCK - JUMP FORWARDS {jump} ({str(last_payload)} -> {str(current_payload)})")
            if not seen:
                if last_payload >= current_payload:
                    jump_back += 1
                    jump = str(last_payload - current_payload)
                    log_order(f"Test run: {test_run} JUMP BACKWARDS {jump} ({str(last_payload)} -> {str(current_payload)})")
                elif last_payload + 1 < current_payload:
                    jump_forward += 1
                    jump = str(current_payload - last_payload)
                    log_order(f"Test run: {test_run} JUMP FORWARDS {jump} ({str(last_payload)} -> {str(current_payload)})")

            last_payload = current_payload
            messages_sent[current_payload].append(msg_id)
                        
            if received_count % 50000 == 0:
                log(f"Received: {received_count} Curr Entry: {msg_entry}")

        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            
            if 'Pulsar error: TimeOut' in message:
                break
            else:
                log(message)
    
    log(f"Read phase complete with message {msg.message_id()}")

topic_prefix = sys.argv[1]
test_num = int(sys.argv[2])
count = int(sys.argv[3])
action_mark = int(sys.argv[4])
test_type = sys.argv[5]
ensemble_size = "2"
write_quorum = "2"
ack_quorum = "2"
slow = "true"
owner = ""

# create log files
start_time = datetime.now().strftime('%H:%M:%S')
output_file_w = open(f"test-output/{topic_prefix}_dedup_output.txt", "w")
output_file_w.write("Dedup,TestRun,SendCount,AckCount,PosAckCount,NegAckCount,Received,NotReceived,ReceivedNoAck,MsgsWithDups,DJF,DJB,JF,JB\n")
output_file = open(f"test-output/{topic_prefix}_dedup_output.txt", "a")
order_file_w = open(f"test-output/{topic_prefix}_order_output.txt", "w")
order_file_w.write("Log of duplicate blocks and out-of-order messages")
order_file = open(f"test-output/{topic_prefix}_order_output.txt", "a")

# create cluster
dedup_enabled_values = ["false", "true"]
timeout_values = [60000, 0]
for i in range(2):
    test_run = 1
    dedup_enabled = dedup_enabled_values[i]
    timeout = timeout_values[i]
    log(f"Running {test_num} runs with deduplication enabled = {dedup_enabled}")
    create_cluster(ensemble_size, write_quorum, ack_quorum, dedup_enabled, slow)
    while test_run <= test_num:

        # run test
        topic = f"{topic_prefix}_{str(test_run)}_dedup_{dedup_enabled}"
        send_count = 0
        ack_count = 0
        pos_ack_count = 0
        neg_ack_count = 0
        action_performed = False
        duplicate_jump_forward = 0
        duplicate_jump_back = 0
        jump_forward = 0
        jump_back = 0
        
        # - CHAOS VARIABLES
        partitions = list()
        owner

        log(f"")
        log(f"Test Run #{test_run} on topic {topic}  ------------")
        
        # - WRITE PHASE --------------------
        log("-------------------------------------------------")
        log("WRITE PHASE")
        log("-------------------------------------------------")
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
                            send_timeout_millis=timeout,
                            properties={
                                "producer-name": "test-producer-name",
                                "producer-id": "test-producer-id"
                            })


        try:
            produce(producer)
            log("Produce ended")
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
            log("Closing producer")
            producer.close()
            log("Producer closed")

        # - READ PHASE --------------------
        time.sleep(10)
        log("-------------------------------------------------")
        log("READ PHASE")
        log("-------------------------------------------------")
        received_count = 0
        message_id = pulsar.MessageId.earliest
        conn_attempts = 1
        while True:
            proxy_ip = get_proxy_ip()
            try:
                reader = client.create_reader(f'persistent://vanlightly/cluster-1/ns1/{topic}', message_id)
                break
            except Exception:
                if conn_attempts > 3:
                    log("Could not connect, aborting test run")
                    client. close()
                    sys.exit(1)
                else:
                    log("Failed to connect, will retry")
                    time.sleep(5)
            
                conn_attempts += 1

        try:
            read(reader)
        except KeyboardInterrupt:
            log("Reader cancelled")
            sys.exit(1)
        finally:
            reader.close()
            client.close()

        not_received = 0
        received_no_ack = 0
        msgs_with_dups = 0
        received = 0
        for msg_val, msg_ids in messages_sent.items():
            received += len(msg_ids)
            if len(msg_ids) == 0 and msg_val in messages_pos_acked:
                not_received += 1
            elif len(msg_ids) == 1 and msg_val not in messages_pos_acked:
                received_no_ack += 1
            elif len(msg_ids) > 1:
                msgs_with_dups += 1

        log("Results --------------------------------------------")
        log(f"Final send count: {str(send_count)}")
        log(f"Final ack count: {str(ack_count)}")
        log(f"Final positive ack count: {str(pos_ack_count)}")
        log(f"Final negative ack count: {str(neg_ack_count)}")
        log(f"Messages received: {str(received)}")
        log(f"Acked messages missing: {str(not_received)}")
        log(f"Non-acked messages received: {str(received_no_ack)}")
        log(f"Duplicates: {msgs_with_dups}")
        log(f"Duplicate Jump Forward: {duplicate_jump_forward}")
        log(f"Duplicate Jump Back: {duplicate_jump_back}")
        log(f"Non-Duplicate Jump Forward: {jump_forward}")
        log(f"Non-Duplicate Jump Back: {jump_back}")
        log("----------------------------------------------------")

        log(f"{dedup_enabled},{str(test_run)},{str(send_count)},{str(ack_count)},{str(pos_ack_count)},{str(neg_ack_count)},{str(received)},{str(not_received)},{str(received_no_ack)},{msgs_with_dups},{str(duplicate_jump_forward)},{str(duplicate_jump_back)},{str(jump_forward)},{str(jump_back)}", True)

        # start the killed broker ready for the next test, with a little wait to give it time to join

        if test_type == "isolate-topic-owner":
            resolve_partition()

        start_downed_broker()
        time.sleep(20)
        test_run += 1


