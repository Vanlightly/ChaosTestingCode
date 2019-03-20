# Notes on Test Run 1 of SAC Test with Quorum Queues

## Test Design
One publisher sends messages with a monotonically increasing integer. Three consumers, each at first connected to a different broker in the cluster.

Publisher and consumers log every 5000th messages sent/received. Consumers also log every message that is:
- a duplicate
- redelivered=true
- out-of-order

The test consists of 10 separate runs, each with a new cluster. Each run consists of:
- the publisher sending messages constantly
- the three consumers trying to consume constantly
- 20 actions performed by the test runner. Those actions can be starting/stopping consumers, or performing a chaos and repair action, such as killing a node then 2 minutes later bringing it back up.

The invariants/properties being tested are:
1. ONE ACTIVE: only one active consumer at a time (safety property)
2. EVENTUAL FAIL-OVER: If the active consumer fails, given time, another consumer will become the new active consumer (liveness property)

The detection mechanisms are:
- ONE ACTIVE: The order of messages jumping forwards-backwards-forwards, when redelivered=false and it is not a duplicate. This is not a perfect detection mechanism as it can be a false positive (due to the violation of FIFO delivery guarantees which is a different invariant)
- EVENTUAL FAIL-OVER: A grace period is provided at the end of the test run to allow consumption to catch up with the publisher. If consumption does not catch up it indicates that potentially, a failover did not take place.

Both detection mechanisms are not perfect and can result in false positives due to ordering and message loss bugs. So manual review of the logs of a failed run is required.

## Log output
You can tell the consumers apart as they are numbered in the following format: [run]-con-[number]. There are always three consumers (0, 1, and 2) that are either connected or not-connected.

For example: CONSUMER(9-con-1) indicates that it is the consumer 1 of run 9.

Publisher and consumers log every 5000th message sent/received. Consumers also log every message that is:
- a duplicate
- redelivered=true
- out-of-order

## Test Results Summary

No cases of two consumers concurrently in active state detected. However, other known and not known bugs were detected.

### EVENTUAL FAIL-OVER
Multiple false positives of EVENTUAL FAIL-OVER due to existing bug in Beta 3 related to SAC queue not releasing messages back to queue on connection failure.

### ONE ACTIVE

Test run 9 saw a false positive test failure, with a case of out-of-order messages WITH redelivered=false, which is a violation of the message ordering guarantee which claims redelivered=false messages will always be delivered in FIFO order. This can be considered a bug.

Can see this in accompanying log test-sac-qq-1.log between lines 4458 and 4614. Note that only the messages that either jump back or forward are printed. 

So for example:
05:55:35.074764 : CONSUMER(9-con-1)->172.20.0.4 : b'a=123201' Last-acked=123552 JUMP BACK 351  
05:55:35.074988 : CONSUMER(9-con-1)->172.20.0.4 : b'a=123553' Last-acked=123201 JUMP FORWARD 352  
05:55:35.203811 : CONSUMER(9-con-1)->172.20.0.4 : b'a=123202' Last-acked=123600 JUMP BACK 398  
05:55:35.215150 : CONSUMER(9-con-1)->172.20.0.4 : b'a=123601' Last-acked=123209 JUMP FORWARD 392

indicates a sequence of: 
123552,
123201, 
123553, 
123554, 
123555, 
123556, 
..., 
123600, 
123202, 
123203, 
123204, 
123205, 
123206, 
123207, 
123208, 
123209, 
123601

### Other

Multiple cases of out-of-order delivery after active consumer failover, with redelivered=true. This is normal though unfortunate.
