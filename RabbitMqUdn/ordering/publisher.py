#!/usr/bin/env python
import pika
from pika import spec
import sys
import time
import subprocess

class Publisher:
    count = 0
    queue = ""
    confirmed = 0
    errors = 0
    published = 0
    curr_pos = 0
    curr_del_tag = 0
    last_acked = 0
    tracker = 0
    terminate = False
    final_ctr = 0
    exit_triggered = False

    node_names = ['rabbitmq1', 'rabbitmq2', 'rabbitmq3']
    nodes = list()

    def __init__(self):
        print("Start up")

    def get_node_index(self, node_name):
        index = 0
        for node in self.node_names:
            if node == node_name:
                return index

            index +=1

        return -1

    def on_open(self, connection):
        connection.channel(self.on_channel_open)
        print("Connection open")

    def print_queue_size_and_close(self, res):
        self.message_count = res.method.message_count
        print(f"{str(message_count)} messages in the queue")
        lost = self.confirmed - message_count
        if lost < 0:
            lost = 0
        
        print(f"{str(lost)} messages lost")
        self.terminate = True
        self.connection.close()
        #exit(0)

    def exit_program(self):
        self.shutdown = True
        if self.last_acked < self.curr_del_tag:
            if self.final_ctr <= 3:
                print(f"Waiting an extra 5 seconds for last acks. Pending: {str(self.curr_del_tag)} Current: {str(self.last_acked)}")
                self.final_ctr += 1
                self.shutdown = False
                self.connection.add_timeout(5, self.exit_program)
            else:
                print("Timeout exceeded, will not wait for further pending acks")
                self.shutdown = True
        
        if self.shutdown:
            print("Results -------------")
            print(f"Success: {str(self.confirmed)}")
            print(f"Failed: {str(self.errors)}")
            print(f"No Response: {str(self.count - (self.confirmed + self.errors))}")
            self.channel.queue_declare(callback=self.print_queue_size_and_close, queue=self.queue, durable=True)
            while(self.terminate == False):
                time.sleep(1)
            print("All messages published and connection closed")            

    def publish_messages(self):
        for num in range(self.curr_pos, self.count):
            if self.channel.is_open:
                self.curr_del_tag += 1
                self.channel.basic_publish('', self.queue,
                                    str(num),
                                    pika.BasicProperties(content_type='text/plain',
                                                            delivery_mode=2))
                self.published += 1
                self.curr_pos += 1
                
                # don't let the publishing advance further than 10000 messages past acks
                if self.curr_del_tag - self.last_acked > 9999:
                    if self.channel.is_open:
                        self.connection.add_timeout(5, self.publish_messages)
                    break
            else:
                print("Channel closed, ceasing publishing")
                break

        if self.curr_pos == self.count and self.exit_triggered == False:
            self.exit_triggered = True
            self.exit_program()

    def on_channel_open(self, chan):
        self.curr_del_tag = 0
        self.last_acked = 0
        chan.confirm_delivery(self.on_delivery_confirmation)
        self.channel = chan
        self.publish_messages()

    def on_delivery_confirmation(self, frame):
        if isinstance(frame.method, spec.Basic.Ack):
            if frame.method.multiple == True:
                self.confirmed += frame.method.delivery_tag - self.last_acked
                self.last_acked = frame.method.delivery_tag
            else:
                self.confirmed += 1
                self.last_acked += 1
        else:
            if frame.method.multiple == True:
                self.errors += frame.method.delivery_tag - self.last_acked
                self.last_acked = frame.method.delivery_tag
            else:
                self.errors += 1
                self.last_acked += 1

        # print out the current ack stats every 10k messages or so
        tmp = self.last_acked / 10000
        if tmp > self.tracker:
            print("Success: " + str(self.confirmed) + " Failed: " + str(self.errors))
            self.tracker = tmp


    def on_close(self, connection, reason_code, reason_text):
        connection.ioloop.stop()
        print("Connection closed. Reason: " + reason_text)

    def reconnect(self):
        self.curr_node += 1
        if self.curr_node > 2:
            print("Failed to connect. Will retry in 5 seconds")
            time.sleep(5)
            self.curr_node = 0
        
        self.connect()

    def connect(self):
        print("Connecting to " + self.nodes[self.curr_node])
        parameters = pika.URLParameters('amqp://jack:jack@' + self.nodes[self.curr_node] + ':5672/%2F')
        self.connection = pika.SelectConnection(parameters=parameters,
                                    on_open_callback=self.on_open,
                                    on_open_error_callback=self.reconnect,
                                    on_close_callback=self.on_close)

        try:
            self.connection.ioloop.start()
        except KeyboardInterrupt:
            self.connection.close()
            self.connection.ioloop.stop()
            self.terminate = True

    def get_node_ip(self, node_name):
        bash_command = "bash ../cluster/get-node-ip.sh " + node_name
        process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        ip = output.decode('ascii').replace('\n', '')
        return ip

    def publish(self, queue, msg_count, connect_node):
        self.count = msg_count
        self.queue = queue
        
        for node_name in self.node_names:
            self.nodes.append(self.get_node_ip(node_name))

        self.curr_node = self.get_node_index(connect_node)

        # keep running until the terminate signal has been received
        while self.terminate == False:
            try:
                self.connect()
            except Exception as ex:
                template = "An exception of type {0} occurred. Arguments:{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                print(message)
                if self.terminate == False:
                    self.reconnect()

