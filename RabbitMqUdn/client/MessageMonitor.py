import time
from collections import deque

from printer import console_out

class MessageMonitor:
    def __init__(self, print_mod):
        self.msg_queue = deque()
        self.msg_set = set()
        self.last_consumer_id = ""
        self.last_consumer_tag = ""
        self.keys = dict()
        self.receive_ctr = 0
        self.print_mod = print_mod
        self.out_of_order = False
        self.concurrent_consumers = False
        self.stop = False

    def append(self, message_body, consumer_tag, consumer_id, actor, redelivered):
        self.msg_queue.append((message_body, consumer_tag, consumer_id, actor, redelivered))

    def stop_processing(self):
        self.stop = True

    def process_messages(self):
        console_out("monitor started", "MONITOR")
        while self.stop == False:
            try:
                msg_tuple = self.msg_queue.popleft()
                self.consume(msg_tuple[0], msg_tuple[1], msg_tuple[2], msg_tuple[3], msg_tuple[4])
            except IndexError:
                time.sleep(1)
            except Exception as e:
                template = "An exception of type {0} occurred. Arguments:{1!r}"
                message = template.format(type(e).__name__, e.args)
                console_out(message, "MONITOR")
                time.sleep(1)
                

        console_out("Monitor exited", "MONITOR")

    def consume(self, message_body, consumer_tag, consumer_id, actor, redelivered):
        self.receive_ctr += 1
        body_str = str(message_body, "utf-8")
        parts = body_str.split('=')
        key = parts[0]
        curr_value = int(parts[1])

        if self.last_consumer_tag != consumer_tag:
            console_out(f"CONSUMER CHANGE! Last id: {self.last_consumer_id} New id: {consumer_id} Last tag: {self.last_consumer_tag} New tag: {consumer_tag}", actor)
            self.last_consumer_id = consumer_id
            self.last_consumer_tag = consumer_tag
        
        if body_str in self.msg_set:
            duplicate = f"DUPLICATE"
            is_dup = True
        else:
            duplicate = ""
            is_dup = False

        if redelivered:
            redelivered_str = "REDELIVERED"
        else:
            redelivered_str = ""

        self.msg_set.add(body_str)

        if key in self.keys:
            last_value = self.keys[key]
            
            if last_value + 1 < curr_value:
                jump = curr_value - last_value
                last = f"Last-acked={last_value}"
                console_out(f"{message_body} {last} JUMP FORWARD {jump} {duplicate} {redelivered_str}", actor)
            elif last_value > curr_value:
                jump = last_value - curr_value
                last = f"Last-acked={last_value}"
                console_out(f"{message_body} {last} JUMP BACK {jump} {duplicate} {redelivered_str}", actor)
                if is_dup == False and redelivered == False:
                    self.out_of_order = True
            elif self.receive_ctr % self.print_mod == 0:
                console_out(f"Sample msg: {message_body} {duplicate} {redelivered_str}", actor)
            elif is_dup or redelivered:
                console_out(f"Msg: {message_body} {duplicate} {redelivered_str}", actor)
        else:
            if curr_value == 1:
                console_out(f"Latest msg: {message_body} {duplicate} {redelivered_str}", actor)
            else:
                console_out(f"{message_body} JUMP FORWARD {curr_value} {duplicate} {redelivered_str}", actor)
                # self.out_of_order = True
        
        self.keys[key] = curr_value

    def stop_consuming(self):
        self.stop = True

    def get_msg_set(self):
        return self.msg_set

    def get_receive_count(self):
        return self.receive_ctr

    def get_unique_count(self):
        return len(self.msg_set)

    def get_out_of_order(self):
        return self.out_of_order