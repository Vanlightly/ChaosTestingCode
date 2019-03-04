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
    state_count = int(get_mandatory_arg(args, "--keys"))
    dup_rate = float(get_optional_arg(args, "--dup-rate", "0"))
    routing_key = get_optional_arg(args, "--rk", "hello")
    queue = get_optional_arg(args, "--queue", None)
    partitioned = get_optional_arg(args, "--partitioned", "false")
    exchanges_arg = get_optional_arg(args, "--exchanges", "")
        
    message_type = "sequence"
    if partitioned == "true":
        if queue != None:
            print("Cannot set partitioning mode and set a queue. Must publish to an exchange")
            exit(1)
        message_type = "partitioned-sequence"

    publisher = RabbitPublisher(node_count, connect_node)

    if queue != None:
        print("direct to queue publishing")
        publisher.publish_direct(queue, count, state_count, dup_rate, message_type)
    elif len(exchanges_arg) > 0:
        print("multi-exchange publishing")
        exchanges = exchanges_arg.split(",")
        publisher.publish_to_exchanges(exchanges, routing_key, count, state_count, dup_rate, message_type)
    else:
        print("single exchange publishing")
        publisher.publish(exchange, routing_key, count, state_count, dup_rate, message_type)

if __name__ == '__main__':
    main()


