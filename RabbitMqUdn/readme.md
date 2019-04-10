# Introduction

The code in RabbitMqUdn folder is under active development. Once it is stable I will fully document it.

The code has been developed with Python 3.6.6

## General Environment setup

### Create a virtualenv and install dependencies

```bash
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

```bash
python publish.py --queue myqueue --msgs 1python create-quorum-queue.py rabbitmq1 Test1 3 rabbitmq3
```

Send 10000 messages to the exchange "orderpython create-quorum-queue.py rabbitmq1 Test1 3 rabbitmq3

```bash
python publish.py --ex orders --msgs 10000python create-quorum-queue.py rabbitmq1 Test1 3 rabbitmq3
```

Send 10000 messages to the exchanges orders1, orders2 and orders3

```bash
python publish.py --exchanges orders1,orders2,orders3 --msgs 10000
```

There are more arguments, please check the script.

#### publish-sequence.py

You can send monotonically increasing integer sequences. Additionally, you send multiple sequences with different keys, for example: a=1 b=1 c=1 a=2 b=2 c=2...

This script does not auto declare any exchanges or queues. The consumer scripts declare exchanges and queues so you can start the consumers first, or manually declare them.

Send one sequence of 10000 messages to the queue "myqueue"

```bash
python publish-sequence.py --queue myqueue --msgs 10000 --keys 1
```

Send five sequences of 10000 messages to the queue "myqueue"

```bash
python publish-sequence.py --queue myqueue --msgs 10000 --keys 5
```

Send five sequences of 10000 messages to the exchange "orders"

```bash
python publish-sequence.py --ex orders --msgs 10000 --keys 5
```

Send five sequences of 10000 messages to the exchanges orders1, orders2 and orders3

```bash
python publish-sequence.py --exchanges orders1,orders2,orders3 --msgs 10000 --keys 5
```

### Consumers

There is a MultiTopicConsumer class that can perform multiple consumer roles, plus additional scripts that use that class for specific purposes.

#### ordering-consumer.py

Consume from a queue that binds to one or more fanout exchanges. Then start consuming and detect message ordering issues. It assumes the use of the publish-sequence.py script as the source of messages.

```bash
python ordering-consumer.py --queue q1 --exchanges topic1,topic2,topic3,topic4,topic5
```

## RabbitMQ v3.8 Testing

### Create a docker image

Note that the 3.8.0-beta 2 and 3 binaries are available. Each use the latest erlang image as a base.

```bash
$ cd RabbitMqUdn/v3.8.0-beta.3
$ docker build -t jackvanlightly/rabbitmq-v3.8.0-beta.3.erl.alpine .
$ cd management
$ docker build -t jackvanlightly/rabbitmq-mgmt-v3.8.0-beta.3.erl.alpine .
```

### Quorum Queues Test

#### Manual test steps using python client and blockade

Create a quorum queue Test1 with rep factor of 3, with leader on rabbitmq3.

First ensure that the cluster/blockade-files/blockade-rmq-3b-3.8.yml has the correct image of RabbitMQ that you want to test. Then run the following:

```bash
$ cd RabbitMqUdn/automated
$ bash setup-test-run.sh 3 3.8
$ cd ../cluster
$ python create-quorum-queue.py rabbitmq1 Test1 3 rabbitmq3
```

You can now perform various tests on the Test1 quorum queue.

Note that create-quorum-queue-sac.py creates a quorum queue with Single Active Consumer enabled.

#### Automated tests

The script client/quorum-queue-test.py runs an automated randomized test and verifies the following invariants:

- no message loss
- no out-of-order messages

A note on message ordering:

Messages are received out-of-order if messages jump forwards then backwards then forwards.
For example:
1,2,5,6,3,4,7,8,9,10

Valid mis-ordering, according to AMQP are:
Messages can jump back and be duplicates, for example:

1,2,3,4,5,3,4,5,6,7,8,9,10

Messages can jump forward only (this could indicate message loss but not an ordering issue):

1,2,3,4,8,9,10

Messages can jump back when redelivered=true.

```bash
$ python -u quorum-queue-test.py --queue q --tests 20 --actions 20 --grace-period-sec 300 --in-flight-max 100  2>&1 | tee test.log
```

### Single Active Consumer Test

#### Test Design

One publisher sends messages with a monotonically increasing integer. Three consumers, each at first connected to a different broker in the cluster.

Consumers post all their consumed (and acked) messages to an in-memory queue which is read by the MessageMonitor class. This class is responsible for:

- detecting active consumer change
- detecting out-of-order messages
- printing messages that are duplicates and redelivered=true
- printing each 5000th message

The test consists of X number separate runs, each with a new cluster. Each run consists of:

- the publisher sending messages constantly
- the three consumers trying to consume constantly
- 10 minutes of chaos and consumer actions. Those actions can be starting/stopping consumers, or performing a chaos and repair action, such as killing a node then 2 minutes later bringing it back up.

The invariants/properties being tested are:

1. ONE ACTIVE: only one active consumer at a time (safety property)
2. EVENTUAL FAIL-OVER: If the active consumer fails, given time, another consumer will become the new active consumer (liveness property)

The detection mechanisms are:

- ONE ACTIVE: When the MessageMonitor sees that the monotonic integer jumps backwards and redelivered=false and it is not a duplicate. This is not a perfect detection mechanism as it can be a false positive (due to the violation of FIFO delivery guarantees which is a different invariant)
- EVENTUAL FAIL-OVER: A grace period is provided at the end of the test run to allow consumption to catch up with the publisher. If consumption does not catch up it indicates that potentially, a failover did not take place.

Both detection mechanisms are not perfect and can result in false positives due to ordering and message loss bugs. So manual review of the logs of a failed run is required.

#### Running the test

The test can be run again mirrored or quorum queues.

Quorum queues

```bash
$ python -u sac-test.py --queue beta3 --tests 10 --run-minutes 10 --grace-period-sec 300 --in-flight-max 200 --cluster 3 --consumers 5 --queue-type quorum  2>&1 | tee test-sac.log
```

Mirrored queues

```bash
$ python -u sac-test.py --queue beta3 --tests 10 --actions 20 --grace-period-sec 300 --in-flight-max 200 --cluster 3 --consumers 5 --queue-type mirrored  2>&1 | tee test-sac.log
```

### Random Test

A test script that is highly configurable, to perform automated or manual testing on quorum or mirrored queues, with or without SAC enabled. See the client/examples/random folder for examples.