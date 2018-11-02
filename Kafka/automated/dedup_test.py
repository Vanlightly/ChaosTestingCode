#!/usr/bin/env python
from confluent_kafka import Producer, Consumer, KafkaError
import sys
import time
import subprocess
from datetime import datetime
import threading
from collections import defaultdict
import re
import uuid

def log(text, to_file=False):
    global output_file
    print(text)
    if to_file:
        output_file.write(f"{text}\n")
        output_file.flush()

def log_order(text):
    global order_file
    time_now = datetime.now().strftime('%H:%M:%S')
    print(text)
    order_file.write(f"{time_now}: {text}\n")
    
def create_cluster():
    subprocess.call(["./setup-dedup-test-run.sh"])

def kill_tcp_connections_of_leader():
    global leader
    port = ""
    if leader == "kafka1":
        port = "9092"
    elif leader == "kafka2":
        port = "9093"
    elif leader == "kafka3":
        port = "9094"

    cmd = f"sudo timeout 10s sudo tcpkill -i docker0 -9 port {port}"
    subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)

# not used at this time
def blackhole_leader():
    global leader
    ip = ""
    if leader == "kafka1":
        ip  = "172.17.0.3"
    elif leader == "kafka2":
        ip  = "172.17.0.4"
    elif leader == "kafka3":
        ip  = "172.17.0.5"

    cmd = f"sudo ip route add blackhole {ip}"
    subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    time.sleep(5)
    cmd = f"sudo ip route delete blackhole {ip}"
    subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    

def create_topic(topic):
    bash_command = f"bash create-topic-print-leader.sh {topic}"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    leader_num = output.decode('ascii').replace('\n', '')
    leader = f"kafka{leader_num}"
    return leader

def get_live_nodes():
    bash_command = "bash ../cluster/list-live-nodes.sh"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    nodes_line = output.decode('ascii').replace('\n', '')
    return nodes_line.split(' ')

def kill_partition_leader():
    global leader
    subprocess.call(["./execute-chaos.sh", "kill-specific-node", leader])

def start_downed_broker():
    global leader
    subprocess.call(["./execute-chaos.sh", "start-specific-node", leader])

def get_broker_ips():
    bash_command = "bash ../cluster/list-broker-ips.sh"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    nodes_line = output.decode('ascii').replace('\n', '')
    return nodes_line.rstrip(' ').replace(' ',',')

def produce_with_java(topic, count, bootstrap_servers, pos_acked_file_path, neg_acked_file_path, enable_idempotency):
    global messages_sent, messages_pos_acked, messages_neg_acked
    cmd = f"java -jar ../KafkaDedup/build/libs/KafkaDedup-all-1.0.jar {topic} {count} {bootstrap_servers} {pos_acked_file_path} {neg_acked_file_path} {enable_idempotency}"
    process = subprocess.Popen(
        cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    action_taken = False
    while True:
        out = process.stdout.readline().decode("ascii")
        if out == '' and process.poll() != None:
            break
        if out != '':
            if out.startswith("50000") and action_taken == False:
                action_taken = True
                if test_type == "kill-leader":
                    print(f"Killing partition leader: {leader}")
                    r = threading.Thread(target=kill_partition_leader)
                    r.start()
                else:
                    print(f"Preparing to kill client connections to partition leader: {leader}")
                    r = threading.Thread(target=kill_tcp_connections_of_leader)
                    r.start()
            elif out == "FINISHED":
                break
            print(out)

    for i in range(0, count):
        messages_sent[str(i)] = list()

    # load pos acked
    file = open(pos_acked_file_path)
    for line in file:
        messages_pos_acked.add(str(int(line)))

    # load neg acked
    file = open(neg_acked_file_path)
    for line in file:
        messages_neg_acked.add(str(int(line)))

# def delivery_report(err, msg):
#     global messages_pos_acked, messages_neg_acked, send_count, ack_count, pos_ack_count, neg_ack_count, action_mark, action_performed, topic, test_type
#     ack_count += 1
#     if err:
#         neg_ack_count += 1
#         value = int(msg.value())
#         messages_neg_acked.add(value)
#     else:
#         pos_ack_count += 1
#         value = int(msg.value())
#         messages_pos_acked.add(value)

#     if ack_count % 50000 == 0:
#         log(f"Send count: {str(send_count)} Ack count: {str(ack_count)} Pos: {str(pos_ack_count)} Neg: {str(neg_ack_count)}")    

#     if ack_count > action_mark and action_performed == False:
#         action_performed = True

#         if test_type == "kill-leader":
#             print(f"Preparing to kill partition leader: {leader}")
#             r = threading.Thread(target=kill_partition_leader)
#             r.start()
#         else:
#             print(f"Preparing to kill client connections to partition leader: {leader}")
#             r = threading.Thread(target=kill_tcp_connections_of_leader)
#             r.start()

# def produce():
#     global send_count, ack_count, pos_ack_count, neg_ack_count, messages_sent, messages_pos_acked, partitions, leader

#     dedup = dedup_enabled == "true"
#     acks_mode = "all"
#     bootstrap_servers = get_broker_ips()
#     log(f"Producer bootstrap.servers: {bootstrap_servers}")

#     producer = Producer({'bootstrap.servers': bootstrap_servers,
#             'message.send.max.retries': 3,
#             'max.in.flight.requests.per.connection': 5,
#             #'enable.idempotence': dedup,
#             'default.topic.config': { 'request.required.acks': acks_mode }})

#     # send the first message synchronously, to ensure everything is running ok
#     producer.produce(topic, str(send_count).encode('utf-8'), callback=delivery_report)
#     send_count += 1
#     messages_sent[send_count] = list()
#     producer.poll(0)
#     producer.flush()
    
#     partitions = get_isolate_from_zk_partitions(leader)

#     print("Started producing")
#     # send bulk of messages asynchronously in order to achieve high message rate
#     while send_count < count-1:
#         producer.poll(0)

#         if send_count - ack_count >= 10000: # ensure we don't have more than 10k in flight at a time
#             time.sleep(0.1)
#             #print("Sleeping")
#         else: 
#             producer.produce(topic, str(send_count).encode('utf-8'), callback=delivery_report)
#             messages_sent[send_count] = list()
#             send_count += 1

#     # send last message in order to block until acked
#     # this way we ensure all messages are acked by the end of this function
#     producer.produce(topic, str(send_count).encode('utf-8'), callback=delivery_report)
#     send_count += 1
#     messages_sent[send_count] = list()
#     producer.poll(0)
#     time.sleep(5)
#     producer.flush()
#     log(f"Send count: {str(send_count)} Ack count: {str(ack_count)} Pos: {str(pos_ack_count)} Neg: {str(neg_ack_count)}")    

def partition_assignment(consumer, partitions):
    for p in partitions:
        p.offset = 0
        log("Partition assigned")
    consumer.assign(partitions)

def read():
    global received_count, messages_sent, topic, duplicate_jump_forward, duplicate_jump_back, jump_forward, jump_back

    bootstrap_servers = get_broker_ips()
    log(f"Consumer bootstrap.servers: {bootstrap_servers}")
    consumer = Consumer({
        'bootstrap.servers': bootstrap_servers,
        'group.id': str(uuid.uuid1()),
        'api.version.request': True,
        'enable.auto.commit': True,
        'auto.offset.reset': 'earliest'
    })

    log(f"Subscribing to {topic}")
    consumer.subscribe([topic], on_assign=partition_assignment)
        
    no_msg_count = 0
    last_payload = -1
    in_dup_block = False

    while True:
        try:
            msg = consumer.poll(2.0)
            if msg is None:
                log("No messages")
                no_msg_count += 1
                if no_msg_count > 30:
                    log("Aborting test, no messages to consume")
                    sys.exit(1)
                continue

            no_msg_count = 0

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    log("Consumed all messages")
                    break
                else:
                    log(msg.error())
                    break

            received_count += 1
            msg_offset = msg.offset()
            current_payload = int(msg.value())
            current_payload_str = str(current_payload)
            seen = len(messages_sent[current_payload_str]) > 0

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

            if current_payload_str in messages_sent:
                messages_sent[current_payload_str].append(msg_offset)

            last_payload = current_payload
                        
            if received_count % 50000 == 0:
                log(f"Received: {received_count} Curr Offset: {msg_offset}")

        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            log(message)
    
    log(f"Read phase complete with message {msg.offset()}")
    consumer.close()

topic_prefix = sys.argv[1]
test_num = int(sys.argv[2])
count = int(sys.argv[3])
action_mark = int(sys.argv[4])
test_type = sys.argv[5]


leader = ""

# create log files
start_time = datetime.now().strftime('%H:%M:%S')
output_file_w = open(f"test-output/{topic_prefix}_dedup_output.txt", "w")
output_file_w.write("DedupEnabled,TestRun,SendCount,AckCount,PosAckCount,NegAckCount,Received,NotReceived,ReceivedNoAck,MsgsWithDups,DJF,DJB,JF,JB\n")
output_file = open(f"test-output/{topic_prefix}_dedup_output.txt", "a")
order_file_w = open(f"test-output/{topic_prefix}_order_output.txt", "w")
order_file_w.write("Log of duplicate blocks and out-of-order messages")
order_file = open(f"test-output/{topic_prefix}_order_output.txt", "a")

dedup_enabled_values = ["false", "true"]
timeout_values = [60000, 0]
for i in range(2):
    test_run = 1
    dedup_enabled = dedup_enabled_values[i]
    timeout = timeout_values[i]
    log(f"Running {test_num} runs with deduplication enabled = {dedup_enabled}")
    create_cluster()

    while test_run <= test_num:

        # run test
        topic = f"{topic_prefix}_{str(test_run)}_dedup_{dedup_enabled}"
        leader = create_topic(topic)
        duplicate_jump_forward = 0
        duplicate_jump_back = 0
        jump_forward = 0
        jump_back = 0
        # send_count = 0
        # ack_count = 0
        # pos_ack_count = 0
        # neg_ack_count = 0
        # action_performed = False
        
        # - CHAOS VARIABLES
        partitions = list()

        log(f"")
        log(f"Test Run #{test_run} on topic {topic}  ------------")
        
        # - WRITE PHASE --------------------
        log("-------------------------------------------------")
        log("WRITE PHASE")
        log("-------------------------------------------------")
        messages_sent = defaultdict(list)
        messages_pos_acked = set()
        messages_neg_acked = set()

        # try:
        #     produce()
        #     print("Produce ended")
        # except KeyboardInterrupt:
        #     log("Producer cancelled")
        #     sys.exit(1)
        # except Exception as ex:
        #     template = "An exception of type {0} occurred. Arguments:{1!r}"
        #     message = template.format(type(ex).__name__, ex.args)
        #     log("The producer has failed!!!")
        #     log(message)
        #     sys.exit(1)
        pos_acked_file = f"producer-output/{topic}_pos_acked.txt"
        neg_acked_file = f"producer-output/{topic}_neg_acked.txt"

        try:
            bootstrap_servers = get_broker_ips()
            produce_with_java(topic, count, bootstrap_servers, pos_acked_file, neg_acked_file, dedup_enabled)
            log("Produce ended")
        except KeyboardInterrupt:
            log("Producer cancelled")
            sys.exit(1)
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            log("The Java producer has failed!!!")
            log(message)
            sys.exit(1)

        # - READ PHASE --------------------
        if test_type == "kill-leader":
            start_downed_broker()

        time.sleep(10)
        log("-------------------------------------------------")
        log("READ PHASE")
        log("-------------------------------------------------")
        received_count = 0
        
        try:
            read()
        except KeyboardInterrupt:
            log("Reader cancelled")
            sys.exit(1)

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

        send_count = len(messages_sent)
        ack_count = len(messages_pos_acked) + len(messages_neg_acked)
        pos_ack_count = len(messages_pos_acked)
        neg_ack_count = len(messages_neg_acked)

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

        log(f"{dedup_enabled},{str(test_run)},{str(send_count)},{str(ack_count)},{str(pos_ack_count)},{str(neg_ack_count)},{str(received)},{str(not_received)},{str(received_no_ack)},{str(msgs_with_dups)},{str(duplicate_jump_forward)},{str(duplicate_jump_back)},{str(jump_forward)},{str(jump_back)}", True)

        time.sleep(20)
        test_run += 1