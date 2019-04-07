# Kafka Tests Guide

## A note on the Blockade UDN feature
This KafkaUdn stands for Kafka User Defined Network. It uses the UDN feature of Blockade which obviates the need for the links feature which does not allow two way visibility required in a Kafka cluster. 

There is one one workaround to make Kafka work with Blockade's UDN feature, we must dynamically reconfigure the cluster after start-up to set the correct value for "advertised.listeners". This is because we cannot use the ${DOCKER_HOST_IP} variable in a blockade.yml and each test run creates a new cluster with dynamically assigned IPs. We can only hard-code the IPs in the blockade.yml. TO get around this limitation of Blockade, we use Kafka's dynamic configuration feature to correct the "advertised.listeners" to the dynamically assigned IP once the cluster has been brought up.

## Note on sudo
Some scripts use sudo. In order to run those commands without the need to enter my password I have modified my sudoers file.

ALL=(ALL) NOPASSWD: /usr/sbin/tcpkill, /usr/bin/timeout, /usr/sbin/ip

This is not a recommended approach for a personal Linux machine or any kinds of production machine.

## Different tests

### Automated Random test
Runs a single producer, producing one or more monotonic sequences, each denoted by a letter. 

For example, with a single sequence: a=1, a=2, a=3, a=4 etc.
With 3 sequences: a=1, b=1, c=1, a=2, b=2, c=2 etc

The letter is used as the message key for routing to partitions.

One or more consumers consume the topic and monitor the message for: out-of-order arrival, duplication and message loss.

During the test, brokers are randomly killed and brought back, network partitions occur and consumers are stopped and started. At random intervals.

All tests log the following output:
- Sample of producer messages
- Sample of consumer messages
- When a consumer change occurs (due to rebalancing)
- Any out-of-order messages
- Any duplicate messages
- Any lost messages

Mandatory arguments:
- --tests The number of test runs. Each test run gets a new cluster
- --run-minutes The number of minutes each test run lasts for
- --topic The name of the topic
- --partitions The number of partitions of the topic
- --rep-factor The replication factor of the topic
- --consumers The number of consumers in the consumer group

Optional arguments:
- --acks-mode The acks mode of the producer. Default: all
- --in-flight-max The number of unacknowledged messages the producer can have at any moment. Default: 100
- --sequences The number of monotonic sequences produced. Supports up to 10. Default: 1
- --cluster The number of Kafka brokers in the cluster. Default 3.
- --min-insync-replicas The minimum number of insync replicas required to ack a message. Default: 1
- --unclean-failover Enable/disable unclean failover. Default: false
- --print-mod The sample rate for printing producer and consumer messages. For example 1000 would print every 1000th message.

Example:
```
python random-test.py --tests 1 --run-minutes 10 --consumers 3 --in-flight-max 2000 --grace-period-sec 300 --cluster 3 --topic topic1 --partitions 1 --rep-factor 3 --acks-mode all --sequences 1
```

### Continuous producer-consumer with no chaos
Simply runs a number of consumers and a single producer until you press Ctrl+C. Just like the automated test, the producer will send up to 10 different monotonic sequences, labelled with a letter. The letter is used as the message key for routing to partitions.

Out-of-order messages and duplicate messages will be detected. 

Once the test is underway, on pressing Ctrl+C, the producer will stop producing and allow consumers to catch up if they are behind. Once the consumers have caught up, the program will print out the final stats, including any message loss detected, and stop.

All tests log the following output:
- Sample of producer messages
- Sample of consumer messages
- When a consumer change occurs (due to rebalancing)
- Any out-of-order messages
- Any duplicate messages
- Any lost messages

Mandatory arguments:
- --new-cluster (true/false) Whether to create a new cluster or reuse an already running one. If false then ensure that the topic name does not already exist as the consumers start at the earliest offset and will spuriously log duplicates if messages already exist in that topic.
- --topic The name of the topic
- --partitions The number of partitions of the topic
- --rep-factor The replication factor of the topic
- --consumers The number of consumers in the consumer group

Optional arguments:
- --acks-mode The acks mode of the producer. Default: all
- --in-flight-max The number of unacknowledged messages the producer can have at any moment. Default: 100
- --sequences The number of monotonic sequences produced. Supports up to 10. Default: 1
- --cluster The number of Kafka brokers in the cluster. Default 3.
- --min-insync-replicas The minimum number of insync replicas required to ack a message. Default: 1
- --unclean-failover Enable/disable unclean failover. Default: false
- --print-mod The sample rate for printing producer and consumer messages. For example 1000 would print every 1000th message.

Example:
```
python producer-consumer.py --new-cluster false --consumers 3 --in-flight-max 10 --grace-period-sec 300 --cluster 3 --topic topic7 --partitions 3 --rep-factor 3 --acks-mode all --sequences 10 --print-mod 100
```