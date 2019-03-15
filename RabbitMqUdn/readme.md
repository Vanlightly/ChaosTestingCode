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
python publish.py --queue myqueue --msgs 1python create-quorum-queue.py rabbitmq1 Test1 3 rabbitmq3
```

Send 10000 messages to the exchange "orderpython create-quorum-queue.py rabbitmq1 Test1 3 rabbitmq3
```
python publish.py --ex orders --msgs 10000python create-quorum-queue.py rabbitmq1 Test1 3 rabbitmq3
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
Note that the 3.8.0-beta 2 and 3 binaries are available. Each use the latest erlang image as a base.

```
$ cd RabbitMqUdn/v3.8.0-beta
$ docker build -t jackvanlightly/rabbitmq-v3.8.0-beta.2.erl.alpine .
$ cd management
$ docker build -t jackvanlightly/rabbitmq-mgmt-v3.8.0-beta.2.erl.alpine .
```

### Quorum Queues Test Failure using Blockade

### Test steps using python client and blockade
Create a quorum queue Test1 with rep factor of 3, with leader on rabbitmq3.

First ensure that the cluster/blockade-files/blockade-rmq-3b-3.8.yml has the correct image of RabbitMQ that you want to test. Then run the following:

```
$ cd RabbitMqUdn/automated
$ bash setup-test-run.sh 3 3.8
$ cd ../cluster
$ python create-quorum-queue.py rabbitmq1 Test1 3 rabbitmq3
```

You can now perform various tests on the Test1 quorum queue.