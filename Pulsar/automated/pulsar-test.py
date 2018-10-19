#!/usr/bin/env python
import pulsar
import sys
import time
import subprocess
from datetime import datetime
import threading
from collections import defaultdict
import re

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

def create_cluster(e, qw, qa, brokers, bookies):
    subprocess.call(["./setup-test-run.sh", e, qw, qa, brokers, bookies])

def get_live_nodes():
    bash_command = "bash ../cluster/list-live-nodes.sh"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    nodes_line = output.decode('ascii').replace('\n', '')
    return nodes_line.split(' ')

def get_live_in_zk_brokers():
    bash_command = "bash ../cluster/list-brokers.sh"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    brokers_line = output.decode('ascii').replace('\n', '').replace('[', '').replace(']', '')
    brokers_list = brokers_line.split(', ')
    brokers = list()    
    for broker in brokers_list:
        brokers.append(broker.split(':')[0])

    return brokers

def get_live_broker():
    brokers = get_live_in_zk_brokers()
    return brokers[0]

def get_owner_broker(topic):
    live_broker = get_live_broker()
    bash_command = f"bash ../cluster/find-topic-owner.sh {live_broker} {topic}"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    owner = output.decode('ascii').replace('\n', '')
    return owner

def get_bookie_in_first_ledger():
    live_broker = get_live_broker()
    bash_command = "bash ../cluster/find-bookie-in-first-ledger.sh"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    bookie = output.decode('ascii').replace('\n', '')
    return bookie

def get_last_confirmed_entry(topic):
    broker = get_live_broker()
    bash_command = f"bash ../cluster/find-last-bk-entry.sh {broker} {topic}"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    lac_line = output.decode('ascii').replace('\n', '')
    entry = int(lac_line.split(":")[1].replace("\"", "").replace(",", ""))
    first = int(lac_line.split(":")[0].replace("\"", ""))
    return [first, entry]

def get_entry(msg_id):
    id = str(msg_id)    .replace("(", "").replace(")", "").split(",")
    first = int(id[0])
    entry = int(id[1])
    return [first, entry]

def is_same_entry(last_entry, current_entry):
    return last_entry[0] == current_entry[0] and last_entry[1] == current_entry[1]

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

def get_custom_partitions():
    global chaos_action, partitions
    # format is custom-isolation(node,node|node,node|..)
    m = re.search('^custom-isolation\[(.+?)\]$', chaos_action)
    if m:
        p_text = m.group(1)
        parts = p_text.split('|')
        for i in range(0, len(parts)):
            partitions.append(parts[i])
    else:
        log("Could not identify custom partitions in supplied argument")
        sys.exit(1)

def execute_chaos_action(topic, chaos_action, partitions):
    if chaos_action == "isolate-broker-from-zk" or chaos_action == "isolate-bookie-from-zk":
        subprocess.call(["./execute-chaos.sh", chaos_action, topic, partitions[0], partitions[1], partitions[2]])
    elif chaos_action.startswith("custom-isolation"):
        if len(partitions) == 0:
            log("No custom partition supplied")
            sys.exit(1)
        
        parts = " ".join(partitions)
        subprocess.call(["./execute-chaos.sh", "custom-isolation", topic, parts])
    else:
        subprocess.call(["./execute-chaos.sh", chaos_action, topic])
    

def send_callback(res, msg):
    global messages_pos_acked, messages_neg_acked, send_count, ack_count, pos_ack_count, neg_ack_count, action_mark, action_performed, chaos_action, topic, partitions
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
        r = threading.Thread(target=execute_chaos_action,args=(topic, chaos_action, partitions))
        r.start()
    
def produce(producer):
    global send_count, ack_count, pos_ack_count, neg_ack_count, chaos_action, partitions

    # send the first message synchronously, to ensure everything is running ok
    producer.send(str(send_count).encode('utf-8'))
    messages_pos_acked.add(send_count)
    send_count += 1
    ack_count += 1
    pos_ack_count += 1

    # perform slow to gather information now before fast message producing
    if chaos_action == "isolate-broker-from-zk":
        owner = get_owner_broker(topic)
        partitions = get_isolate_from_zk_partitions(owner, topic)
    elif chaos_action == "isolate-bookie-from-zk":
        bookie = get_bookie_in_first_ledger()
        partitions = get_isolate_from_zk_partitions(bookie, topic)
    elif chaos_action.startswith("custom-isolation"):
        get_custom_partitions()

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
    global out_of_order, received_count, duplicate, messages_sent, test_run, topic
    last_confirmed = get_last_confirmed_entry(topic)
    log(f"Last confirmed entry: {last_confirmed}")

    msg = reader.read_next()
    msg_id = msg.message_id()
    msg_entry = get_entry(msg_id)
    current_payload = int(msg.data())
    lastMsg = msg
    
    received_count = 1
    last_payload = current_payload
    messages_sent[last_payload].append(msg_id)
    reader_timeout = 10000

    log(f"Start reading from {msg_id}")

    while True:
        try:
            msg = reader.read_next(reader_timeout)
            msg_id = msg.message_id()
            msg_entry = get_entry(msg_id)

            # lower the wait time towards the end
            if is_same_entry(last_confirmed, msg_entry):
                reader_timeout = 10000
            else:
                reader_timeout = 60000
            
            current_payload = int(msg.data())
            messages_sent[current_payload].append(msg_id)
                        
            received_count += 1
            if received_count % 50000 == 0:
                log(f"Received: {received_count} Curr Entry: {msg_entry}")
                            
            if last_payload >= current_payload:
                line = f"{test_run}|{lastMsg.message_id()}|{str(last_payload)}|{msg_id}|{current_payload}"
                if len(messages_sent[current_payload]) > 1:
                    duplicate += 1
                    write_duplicate(line)
                else:
                    out_of_order += 1
                    write_out_of_order(line)

            last_payload = current_payload
            lastMsg = msg
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            
            if 'Pulsar error: TimeOut' in message:
                break
            else:
                log(message)
    
    log(f"Read phase complete with message {msg.message_id()}")

def show_help():
    f=open("help", "r")    
    contents =f.read()
    print(contents)

chaos_action = sys.argv[1]

if chaos_action == "help":
    show_help()
    sys.exit(0)
    
topic_prefix = sys.argv[2]
test_num = int(sys.argv[3])
count = int(sys.argv[4])
action_mark = int(sys.argv[5])
bk_config = sys.argv[6].split('-')
ensemble_size = bk_config[0]
write_quorum = bk_config[1]
ack_quorum = bk_config[2]
node_counts = sys.argv[7].split('-')
brokers = node_counts[0]
bookies = node_counts[1]

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
    create_cluster(ensemble_size, write_quorum, ack_quorum, brokers, bookies)

    # run test
    send_count = 0
    ack_count = 0
    pos_ack_count = 0
    neg_ack_count = 0
    action_performed = False

    log(f"", True)
    log(f"Test Run #{test_run} on topic {topic}  ------------", True)

    # - CHAOS VARIABLES
    partitions = list()
        
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

    if chaos_action == "kill-bookie":
        log("Waiting for 20 seconds before starting reader")
        time.sleep(20)

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


