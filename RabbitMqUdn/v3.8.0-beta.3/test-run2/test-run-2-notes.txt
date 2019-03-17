#TEST RUN: beta-3 test run 2 16/03/2019

##Configuration
- 3 nodes
- Pika 0.12
- 1 quorum queue with rep-factor of 3 and Single Active Consumer enabled
- 1 publisher (max in flight at 200 msgs)
- 1 consumer (prefetch 10)

## Invariants tested
### Message loss
A  message is lost when publisher receives a confirm for it but consumer never gets it.

### Message order
Messages are received out-of-order if messages jump forwards then backwards then forwards.
For example:
1,2,5,6,3,4,7,8,9,10

Valid mis-ordering, according to AMQP are:
Messages can jump back and be duplicates, for example:
1,2,3,4,5,3,4,5,6,7,8,9,10

Messages can jump forward only (this could indicate message loss but not an ordering issue):
1,2,3,4,8,9,10

##Log Analysis notes
11/20 test runs produced test failure

Message loss scenario related to consumers.
Messages delivered out-of-order, to investigate repro steps.


- Message loss at line 1017
- Message loss at line 1595
- Message loss at line 2205 (2 lots of 10, 1 of 186)
- Message loss at line 4634
- Out-of-delivery after partition heal at line 5843
- Out-of-delivery after partition start at line 7023
- Message loss at line 7271
- Out-of-delivery after broker start at line 7737
- Message loss at line 9204
- Message loss at line 9771
- Message loss at line 10842
- Out-of-delivery after broker start at line 14036
- Message loss at line 14845

## Message loss investigation
The message loss always matches the prefetch and occurs 
in any chaos action that causes the consumer to lose 
its connection. On reconnection and consuming resumes,
those unacked messages are not redelivered.

Can easily reproduce using the scripts in this repo. Have
two terminal windows in the following folders:
- cluster (with virtualenmv activated)
- client

1. cluster$ cp blockade-files/blockade-rmq-3b-3.8.yml blockade.yml
2. cluster$ blockade up
3. cluster$ python create-quorum-queue-sac.py rabbitmq1 Test1 3 rabbitmq3
4. client$ python publish-sequence.py --queue Test1 --msgs 10000 --key 1 

before client has consumed all 10000 messages kill rabbitmq3
5a. client$ python ordering-consumer.py --queue Test1 --node rabbitmq3
5b cluster$ blockade kill rabbitmq3

You will now see the consumer connect to a different broker and jump 
ahead 11 messages (10 lost messages + next msg).

Sample output of consumer:
10:43:03.256974 : CONSUMER(1)->192.168.192.2 : Sample msg: b'a=1400'  
10:43:03.700730 : CONSUMER(1)->192.168.192.2 : Sample msg: b'a=1500'  
10:43:03.981889 : CONSUMER(1)->192.168.192.2 : Connection was closed, retrying...
10:43:08.987545 : CONSUMER(1)->none : Connection is closed. Opening new connection
10:43:09.016501 : CONSUMER(1)->192.168.192.4 : Consuming queue: Test1 with consumer tag: ctag1.b97a4c03de6c4f109a28f0c580d3f026
10:43:09.016960 : CONSUMER(1)->192.168.192.4 : b'a=1558' Last-acked=1547 JUMP FORWARD 11  
10:43:09.171745 : CONSUMER(1)->192.168.192.4 : Sample msg: b'a=1610'  
10:43:09.462396 : CONSUMER(1)->192.168.192.4 : Sample msg: b'a=1710'  

## Out-of-order delivery investigation
Characteristics:
- All out-of-order deliveries are messages with redelivered=true.
- Occurs when a broker is started being back quorum (bringing live broker count from 1 to 2)

The jumping back and forwards corresponds to the consumer prefetch.
Message ordering guarantees of redelivered messages are best effort only,
which is a shame. Was hoping that Single Active Consumer would enable
rock solid ordering guarantees.