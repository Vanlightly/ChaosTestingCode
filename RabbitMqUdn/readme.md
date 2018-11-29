# Introduction
The code in RabbitMqUdn folder is under active development. Once it is stable I will fully document it.

The code has been developed with Python 3.6.6

## General Environment setup

### Create a virtualenv and install dependencies.

```
$ cd RabbitMqUdn
$ virtualenv venv-rabbit
$ source venv-rabbit/bin/activate
$ pip install -r requirements.txt
```

### Blockade
The RabbitMQ cluster is created in blockade. Various blockade files exist in the /cluster/blockade-files directory. You can create a cluster of your choosing by copying the desired blockade-xxx.yml file to the cluster directory, changing its name to "blockade.yml" then executiung the command "blockade up". To stop the cluster use the command "blockade destroy".

There is also a bash script setup-test-run.sh that will perform a destroy and up command, copying a blockade.yml file according to the parameters to specify. Currently only the version of RabbitMQ can be chosen (3.7 or 3.8). Note that for the 3.8 version you'll need to follow the instructions in the quorum queues section to create a docker image.

## Scripts guide

### Publishers
There is a RabbitPublisher python class that performs various message publishing plus a set of python scripts that use that class that you can use:
- publish.py
- publish-sequence.py
- publish-large-messages.py

#### publish.py

Send 10000 messages to the queue "myqueue"
```
python publish.py --queue myqueue --msgs 10000
```

Send 10000 messages to the exchange "orders"
```
python publish.py --ex orders --msgs 10000
```

Send 10000 messages to the exchanges orders1, orders2 and orders3
```
python publish.py --exchanges orders1,orders2,orders3 --msgs 10000
```

There are more arguments, please check the script.

#### publish-sequence.py
You can send monotonically increasing integer sequences. Additionally, you send multiple sequences with different keys, for example: a=1 b=1 c=1 a=2 b=2 c=2...

This script does not auto declare any exchanges or queues. The consumer scripts declare exchanges and queues so you can start the consumers first, or manually declare them.

Send one sequence of 10000 messages to the queue "myqueue"
```
python publish-sequence.py --queue myqueue --msgs 10000 --keys 1
```

Send five sequences of 10000 messages to the queue "myqueue"
```
python publish-sequence.py --queue myqueue --msgs 10000 --keys 5
```

Send five sequences of 10000 messages to the exchange "orders"
```
python publish-sequence.py --ex orders --msgs 10000 --keys 5
```

Send five sequences of 10000 messages to the exchanges orders1, orders2 and orders3
```
python publish-sequence.py --exchanges orders1,orders2,orders3 --msgs 10000 --keys 5
```

### Consumers
There is a MultiTopicConsumer class that can perform multiple consumer roles, plus additional scripts that use that class for specific purposes.

#### ordering-consumer.py
Consume from a queue that binds to one or more fanout exchanges. Then start consuming and detect message ordering issues. It assumes the use of the publish-sequence.py script as the source of messages.

```
python ordering-consumer.py --queue q1 --exchanges topic1,topic2,topic3,topic4,topic5
```


## RabbitMQ v3.8 Quorum Queue Testing

### Create a docker image
Note that there are a 3.8.0-beta1 and 3.8.0-alpha.333 dockerfiles. Each use the latest erlang image as a base.

```
$ cd RabbitMqUdn/v3.8.0-alpha.333
$ docker build -t jackvanlightly/rabbitmq-v3.8.0-alpha.333 .
$ cd management
$ docker build -t jackvanlightly/rabbitmq-mgmt-v3.8.0-alpha.333 .
```

### Quorum Queues Test Failure using Blockade

Description: This test kills the queue leader node while a publisher is connected to a different node. 

Steps:
- Quorum queue created with leader on rabbitmq3.
- Publisher connects to rabbitmq1.
- Publisher sends 50000 messages, ensuring it never has more than 10000 messages in flight.
- rabbitmq3 killed, leadership fails-over to a follower (rabbitmq1 or rabbitmq2)
- The 10000 or so unacknowledged messages are never acked

Expected behaviour: The same as mirrored queues. The fail-over of the leader to a follower should be transparent. Given that the publisher is not connected to the lost broker, the connection stays alive and the publisher should receive acks/nacks for all the pending messages.

Actual Behaviour: No acks/nacks ever received for messages that were pending an ack at the time of the queue fail-over.

### Test steps using python client and blockade
Create a quorum queue Test1 with rep factor of 3, with leader on rabbitmq3
```
$ cd RabbitMqUdn/automated
$ bash setup-test.sh 3 3.8
$ cd ../cluster
$ python create-quorum-queue.py rabbitmq1 Test1 rabbitmq3
```

Terminal 1
Publish 50000 messages to Test1, but connected to rabbitmq2 (not the leader). 

The publisher pauses publishing when it has more than 10000 unacknowledged messages. Once
the pending acks fall below 10000 again it publishes more messages.


```
$ cd RabbitMqUdn/client
$ python publish.py --node rabbitmq2 --queue Test1 --msgs 50000
Will publish to exchange  and routing key Test2
Attempting to connect to 172.28.0.3
Connection opened: <SelectConnection OPEN socket=('172.28.0.1', 55592)->('172.28.0.3', 5672) params=<URLParameters host=172.28.0.3 port=5672 virtual_host=/ ssl=False>>
Channel opened, publishing to commence
11000 pending messages
10170 pending messages
Pos acks: 10071 Neg acks: 0 Undeliverable: 0
10400 pending messages <-- we kill the leader at this point (see Terminal 2)
10205 pending messages
10727 pending messages
10727 pending messages
10727 pending messages
10727 pending messages
10727 pending messages
10727 pending messages
... forever
```

Terminal 2
Once we get "pos acks" greater than 10000 on Terminal 1, kill rabbitmq3 (the leader)
```
$ cd RabbitMqUdn/cluster
$ blockade kill rabbitmq3
```

You will now see that the publisher in Terminal 1 now waits forever for the pending acks 
of the 10000 so pending messages. With a mirrored queue, there is a brief pause
but publishing is able to continue. With quorum queues, the broker which the
publisher is connected to never sends any ack for the messages that were pending
when the broker that hosted the queue leader was killed.

### Behaviour of Mirrored Queues
If we run the same test again, but this time, instead of running the create-quorum-queue.py script, we run:

Terminal 1
```
$ blockade start rabbitmq3
(wait for the node to rejoin the cluster)
$ python create-ha-queue.py rabbitmq1 Test2 rabbitmq3
```

Now repeat the same Terminal 1 and 2 actions (except publish to queue Test2) and see the publisher completes the sending of all 50000 messages. The master queue dies, but as we are not connected to that node, the connection still lives and the broker handles everything transparently to the publisher. This is the behaviour I expected from quorum queues.