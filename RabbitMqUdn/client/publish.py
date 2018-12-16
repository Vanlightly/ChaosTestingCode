#!/usr/bin/env python
import sys
from command_args import get_args, get_mandatory_arg, get_optional_arg
from RabbitPublisher import RabbitPublisher

def main():
    args = get_args(sys.argv)

    connect_node = get_optional_arg(args, "--node", "rabbitmq1")
    node_count = int(get_optional_arg(args, "--cluster-size", "3"))
    exchange = get_optional_arg(args, "--ex", "")
    count = int(get_mandatory_arg(args, "--msgs"))
    dup_rate = float(get_optional_arg(args, "--dup-rate", "0"))
    routing_key = get_optional_arg(args, "--rk", "hello")
    queue = get_optional_arg(args, "--queue", None)
    message_type = get_optional_arg(args, "--msg-type", "hello")
            
    publisher = RabbitPublisher(node_count, connect_node)

    try:
        if queue != None:
            print("direct")
            publisher.publish_direct(queue, count, 1, dup_rate, message_type)
        else:
            publisher.publish(exchange, routing_key, count, 1, dup_rate, message_type)
    except:
        print("Publishing aborted, final stats:")
        print(publisher.print_final_count())

if __name__ == '__main__':
    main()


