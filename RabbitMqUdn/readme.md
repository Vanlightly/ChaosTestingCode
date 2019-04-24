# Introduction

The code in RabbitMqUdn folder is under active development. Once it is stable I will fully document it.

The code has been developed with Python 3.6.7

## Some notes

You can output all scripts to a file appending "2>&1 | tee my-log-file.log" to the end. Just ensure to use the -u flag when executing this way. For example: 

```bash
$ python -u some-script.py 2>&1 | tee my-log-file.log
```

## General Environment setup

### Create a virtualenv and install dependencies

This codebase uses Python 3.6.

```bash
$ cd RabbitMqUdn
$ python3.6 -m venv venv-rabbit
$ source venv-rabbit/bin/activate
$ pip install -r requirements.txt
```

### Blockade

The RabbitMQ cluster is created in blockade. Various blockade files exist in the /cluster/blockade-files directory. You can create a cluster of your choosing by copying the desired blockade-xxx.yml file to the cluster directory, changing its name to "blockade.yml" then executiung the command "blockade up". To stop the cluster use the command "blockade destroy".

There is also a bash script setup-test-run.sh that will perform a destroy and up command, copying a blockade.yml file according to the parameters to specify. Currently only the version of RabbitMQ can be chosen (3.7 or 3.8). Note that for the 3.8 version you'll need to follow the instructions in the quorum queues section to create a docker image.

Blockade will not pull docker images. Make sure you do a docker pull on any images first.

### RabbitMQ v3.8 Testing

I make docker images available, currently:

- jackvanlightly/rabbitmq-mgmt-v3.8.0-beta.3.erl.alpine:latest
- jackvanlightly/rabbitmq-mgmt-v3.8.0-alpha.613.erl.alpine:latest

If you want to build your own, the dockerfiles can be found in folders v3.8.0-beta.3 and v3.8.0-alpha.613.

```bash
$ cd RabbitMqUdn/v3.8.0-beta.3
$ docker build -t jackvanlightly/rabbitmq-v3.8.0-beta.3.erl.alpine .
$ cd management
$ docker build -t jackvanlightly/rabbitmq-mgmt-v3.8.0-beta.3.erl.alpine .
```

## Publishing and Consuming without chaos

Use the publish-consume.py script. With arguments:

Cluster:

- --new-cluster Defaults to false. When true, a new blockade cluster will be deployed
- --cluster-size The number of brokers (3 or 5)
- --rmq-version The version of RabbitMQ (3.7 or 3.8)

Publish to:

- --queue The queue which consumers consume from. When using direct mode, uses the direct exchange to publish messages directly to this queue. When using exhange mode, a binding from this queue is made to the exchange.
- --exchanges Send messages to one or more exchanges. Comma separated. Only in exchange mode.

Send what:

- --pub-mode Either "direct" or "exchange". Defaults to direct.
- --msg-mode One of 4 modes. "sequence" to send monotonic sequences. "partitioned-sequence" to use a separate routing key per sequence (not useful at this point - more coming soon). "large-msgs" to send large messages. "hello" to send a small message that says hello. Defaults to sequence.
- --msgs The number of messages to send
- --sequences When using either sequence mode, the number of monotonic sequences to send. Each sequence is identified by a key to differentiate themselves. Messages are in the format key=number.
- --dup-rate Introduce duplicate messages. Float between 0 and 1, for example 0.2 would be 20% duplicate rate. Default is 0.
- --in-flight-max The maximum number of unconfirmed messages allowed at any one moment. Higher gives better throughput.
- --connect-node The broker to connect to initially. Defaults to rabbitmq1

Consumers:

- --consumers The number of consumers. They will consume from the queue --queue. Defaults to one consumer
- --analyze Analyze message ordering and message duplication or not. Default to true. Best to turn off when using multiple publishers, or not using sequences.

Example 1: Send a single 10000 long monotonic sequence to the queue "q1" on an existing cluster with one publisher and one consumer

```bash
python publish-consume.py --new-cluster false --queue q1 --msgs 100000
```

Example 2: Send a single 10000 long monotonic sequence to the queue "q1" on an existing cluster with one publisher and one consumer. With a high in-flight-max we get much higher throughput than example 1.

```bash
python publish-consume.py --new-cluster false --queue q1 --msgs 100000 --in-flight-max 10000
```

Example 3: Sends 10 monotonic sequences each with 100000 messages to the exchange "ex1" on a new cluster and bind a queue q1 to ex1 with one consumer consuming

```bash
python publish-consume.py --new-cluster true --cluster-size 3 --rmq-version 3.8 --queue q1 --exchanges ex1 --msgs 100000 --pub-mode exchange --msg-mode sequence --sequences 10
```

Example 4: Send 10000 large messages to the exchange "orders" with a message length of approximately 15000 characters

```bash
python publish-consume.py --new-cluster false --queue orders2 --exchanges orders --msgs 10000 --pub-mode exchange --msg-mode large-msgs --msg-size 15000
```

Example 5: Send a 10000 long sequence to the exchanges orders1, orders2 and orders3

```bash
python publish.py --exchanges orders1,orders2,orders3 --msgs 10000 --pub-mode hello
```

Example 6: Send a single 10000 long monotonic sequence to the quorum queue "qq1" with rep-factor of 3 with Single-Active-Consumer enabled on an existing cluster. Ouorum queues and SAC only on 3.8 clusters.

```bash
python publish-consume.py --new-cluster false --queue qq1 --msgs 100000 --queue-type quorum --rep-factor 3 --sac true
```

Example 7: Send a single 10000 long monotonic sequence to the mirrored queue "mq1" with rep-factor of 3 on an existing cluster.

```bash
python publish-consume.py --new-cluster false --queue mq1 --msgs 100000 --queue-type standard --rep-factor 3
```

## Manual Quorum Queues Test

Create a quorum queue Test1 with rep factor of 3, with leader on rabbitmq3.

First ensure that the cluster/blockade-files/blockade-rmq-3b-3.8.yml has the correct image of RabbitMQ that you want to test. Then run the following:

```bash
$ cd RabbitMqUdn/cluster
$ bash deploy-blockade-cluster.sh 3 3.8
$ python create-quorum-queue.py rabbitmq1 Test1 3 rabbitmq3
```

You can now perform various tests on the Test1 quorum queue.

Note that create-quorum-queue-sac.py creates a quorum queue with Single Active Consumer enabled.

## Automated test Quorum Queues Test

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

Example 1: with Single Active Consumer disabled

```bash
$ python -u quorum-queue-test.py --queue q --tests 20 --actions 20 --grace-period-sec 300 --in-flight-max 100 --sac false  2>&1 | tee test.log
```

Example 2: with Single Active Consumer enabled

```bash
$ python -u quorum-queue-test.py --queue q --tests 20 --actions 20 --grace-period-sec 300 --in-flight-max 100 --sac true  2>&1 | tee test.log
```

## Single Active Consumer Test

### Test Design

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

### Running the test

The test can be run again mirrored or quorum queues.

Quorum queues

```bash
$ python -u sac-test.py --queue beta3 --tests 10 --run-minutes 10 --grace-period-sec 300 --in-flight-max 200 --cluster 3 --consumers 5 --queue-type quorum  2>&1 | tee test-sac.log
```

Mirrored queues

```bash
$ python -u sac-test.py --queue beta3 --tests 10 --actions 20 --grace-period-sec 300 --in-flight-max 200 --cluster 3 --consumers 5 --queue-type mirrored  2>&1 | tee test-sac.log
```

## Random Test

A test script that is highly configurable, to perform automated or manual testing on quorum or mirrored queues, with or without SAC enabled. See the client/examples/random folder for examples.