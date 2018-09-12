import pika
from pika import spec
import sys
import time

confirmed = 0
errors = 0
published = 0
curr_pos = 0
count = int(sys.argv[2])
queue = sys.argv[3]
curr_del_tag = 0
last_acked = 0
tracker = 0
terminate = False
final_ctr = 0
exit_triggered = False

node_names = ['rabbitmq1', 'rabbitmq2', 'rabbitmq3']
nodes = ['172.17.0.2', '172.17.0.3', '172.17.0.4']

def get_node_index(node_name):
    index = 0
    for node in node_names:
        if node == node_name:
            return index

        index +=1

    return -1

def on_open(connection):
    connection.channel(on_channel_open)
    print("Connection open")

def print_queue_size_and_close(res):
    global confirmed, errors, count, terminate
    message_count = res.method.message_count
    print(str(message_count) + " messages in the queue")
    lost = confirmed - message_count
    if lost < 0:
        lost = 0
    
    print(str(lost) + " messages lost")
    terminate = True
    connection.close()
    exit(0)

def exit_program():
    global channel, queue, connection, final_ctr, terminate, last_acked, curr_del_tag, confirmed, errors, count
    shutdown = True
    if last_acked < curr_del_tag:
        if final_ctr <= 3:
            print("Waiting an extra 5 seconds for last acks. Pending: " + str(curr_del_tag) + " Current: " + str(last_acked))
            final_ctr += 1
            shutdown = False
            connection.add_timeout(5, exit_program)
        else:
            print("Timeout exceeded, will not wait for further pending acks")
            shutdown = True
    
    if shutdown:
        print("Results -------------")
        print("Success: " + str(confirmed))
        print("Failed: " + str(errors))
        print("No Response: " + str(count - (confirmed + errors)))
        channel.queue_declare(callback=print_queue_size_and_close, queue=queue, durable=True)
        

def publish_messages():
    global connection, channel, published, count, published, curr_pos, last_acked, curr_del_tag, exit_triggered
    for iteration in xrange(curr_pos, count):
        if channel.is_open:
            curr_del_tag += 1
            channel.basic_publish('', queue,
                                'Hello World!',
                                pika.BasicProperties(content_type='text/plain',
                                                        delivery_mode=2))
            published += 1
            curr_pos += 1
            
            # don't let the publishing advance further than 10000 messages past acks
            if curr_del_tag - last_acked > 9999:
                if channel.is_open:
                    connection.add_timeout(5, publish_messages)
                break
        else:
            print("Channel closed, ceasing publishing")
            break

    if curr_pos == count and exit_triggered == False:
        exit_triggered = True
        exit_program()

def on_channel_open(chan):
    global connection, channel, published, count, published, curr_pos, last_acked, curr_del_tag
    curr_del_tag = 0
    last_acked = 0
    chan.confirm_delivery(on_delivery_confirmation)
    channel = chan
    publish_messages()

def on_delivery_confirmation(frame):
    global confirmed, errors, count, last_acked, tracker
    if isinstance(frame.method, spec.Basic.Ack):
        if frame.method.multiple == True:
            confirmed += frame.method.delivery_tag - last_acked
            last_acked = frame.method.delivery_tag
        else:
            confirmed += 1
            last_acked += 1
    else:
        if frame.method.multiple == True:
            errors += frame.method.delivery_tag - last_acked
            last_acked = frame.method.delivery_tag
        else:
            errors += 1
            last_acked += 1

    # print out the current ack stats every 10k messages or so
    tmp = last_acked / 10000
    if tmp > tracker:
            print("Success: " + str(confirmed) + " Failed: " + str(errors))
            tracker = tmp


def on_close(connection, reason_code, reason_text):
    connection.ioloop.stop()
    print("Connection closed. Reason: " + reason_text)

def reconnect():
    global curr_node
    curr_node += 1
    if curr_node > 2:
        print("Failed to connect. Will retry in 5 seconds")
        time.sleep(5)
        curr_node = 0
    
    connect()

def connect():
    global connection, curr_node, terminate
    print("Attempting to connect to " + nodes[curr_node])
    parameters = pika.URLParameters('amqp://jack:jack@' + nodes[curr_node] + ':5672/%2F')
    connection = pika.SelectConnection(parameters=parameters,
                                on_open_callback=on_open,
                                on_open_error_callback=reconnect,
                                on_close_callback=on_close)

    try:
        connection.ioloop.start()
    except KeyboardInterrupt:
        connection.close()
        connection.ioloop.stop()
        terminate = True

curr_node = get_node_index(sys.argv[1])

# keep running until the terminate signal has been received
while terminate == False:
    try:
        connect()
    except:
        if terminate == False:
            reconnect()

