# Test Report - Test Run of 2019-04-28/29

Quorum and mirrored queues tested with SAC enabled. 15 tests, each test of 10 minutes. Each test checks for message loss and ordering is correct. Messsages with redelivered flag are exempt from message ordering check.

- Mirrored queues, SAC, 5 consumers, prefetch 1000, randomly stop and start consumers, no broker or network chaos.
- Quorum queues, SAC, 5 consumers, prefetch 1000, randomly stop and start consumers, no broker or network chaos.
- Mirrored queues, SAC, 20 consumers, prefetch 10, randomly stop and start consumers, kill-restart brokers, partition and restore network.
- Quorum queues, SAC, 20 consumers, prefetch 10, randomly stop and start consumers, kill-restart brokers, partition and restore network.

## Test Findings

Findings only relate to SAC. Non SAC tests to be run in the future.

Message loss found with quorum and SAC.

### Test chaos-mixed_quorom_sac.sh saw message loss with quorum queues and SAC

Test run and broker logs here: https://s3-eu-west-1.amazonaws.com/vanlightly-rabbitmq-tests/20190429/chaos-mixed_quorom_sac_20190428_2217.zip 

#### On active consumer change, during loss of quorum

With prefetch 10, and consumers ack each message individually.

Pattern:

1. Two of three brokers go down
2. Active consumer asked to stop, logs last acknowledged message.
3. Two down brokers brought back up
4. New consumer becomes active
5. New consumer jumps the 10 messages that were in-flight for previous consumer (message loss)
6. New consumer delivered 10 messages marked as REDELIVERED that were never delivered previously to previous consumer (mislabelled)

Example from chaos-mixed_quorom_sac.sh test 1 (also test 8):

```logs
22:20:33.132186 : CONSUMER (Test:0 Id:C1)->rabbitmq2 : Requested to stop. Last msg received: b'2019-04-28 22:19:29.667554|P1a=23763'
...
22:21:31.411926 : CONSUMER (Test:0 Id:C2)->rabbitmq1 : CONSUMER CHANGE FOR SEQUENCE P1A! Last id: C1 New id: C2 Last tag: ctag1.e3013dd0e57c46bd9bb877a08dcb53c1 New tag: ctag1.becb76491193425cab84dffdd4e2a725
22:21:31.411981 : CONSUMER (Test:0 Id:C2)->rabbitmq1 : P1a=23773 Last-acked=23763 JUMP FORWARD 10  REDELIVERED            [Lag: 121.743956s Sent: 22:19:29.667890]
22:21:31.412026 : CONSUMER (Test:0 Id:C2)->rabbitmq1 : P1a=23774  REDELIVERED            [Lag: 121.744093s Sent: 22:19:29.667922]
22:21:31.412058 : CONSUMER (Test:0 Id:C2)->rabbitmq1 : P1a=23775  REDELIVERED            [Lag: 121.744096s Sent: 22:19:29.667954]
22:21:31.412087 : CONSUMER (Test:0 Id:C2)->rabbitmq1 : P1a=23776  REDELIVERED            [Lag: 121.744093s Sent: 22:19:29.667986]
22:21:31.412138 : CONSUMER (Test:0 Id:C2)->rabbitmq1 : P1a=23777  REDELIVERED            [Lag: 121.74411s Sent: 22:19:29.668018]
22:21:31.412189 : CONSUMER (Test:0 Id:C2)->rabbitmq1 : P1a=23778  REDELIVERED            [Lag: 121.744082s Sent: 22:19:29.668097]
22:21:31.412239 : CONSUMER (Test:0 Id:C2)->rabbitmq1 : P1a=23779  REDELIVERED            [Lag: 121.744095s Sent: 22:19:29.668134]
22:21:31.412288 : CONSUMER (Test:0 Id:C2)->rabbitmq1 : P1a=23780  REDELIVERED            [Lag: 121.744113s Sent: 22:19:29.668166]
22:21:31.412336 : CONSUMER (Test:0 Id:C2)->rabbitmq1 : P1a=23781  REDELIVERED            [Lag: 121.744128s Sent: 22:19:29.668198]
22:21:31.412388 : CONSUMER (Test:0 Id:C2)->rabbitmq1 : P1a=23782  REDELIVERED            [Lag: 121.744148s Sent: 22:19:29.668231]
```

#### On active consumer change, message gap

After a consumer change due to connected broker being killed, new consumer receives messages, but jumping a gap of messages .

Example from chaos-mixed_quorom_sac.sh, test 2 (also test 5, 6, 7)

```logs
22:57:01.239187 : CONSUMER (Test:2 Id:C11)->rabbitmq3 : Connection error. Last msg received: b'2019-04-28 22:57:00.615050|P1a=507464' Error: An exception of type StreamLostError occurred. Arguments:("Stream connection lost: ConnectionResetError(104, 'Connection reset by peer')",)
CHAOS: rabbitmq3 killed
NODE            CONTAINER ID    STATUS  IP              NETWORK    PARTITION  
rabbitmq1       9793336d90c7    UP      192.168.192.2   NORMAL                
rabbitmq2       d2279bb3cea9    UP      192.168.192.3   NORMAL                
rabbitmq3       5fbc7b610b8e    DOWN                    UNKNOWN               
22:57:06.238615 : CONSUMER (Test:2 Id:C4)->rabbitmq3 : Connection is closed. Opening new connection
22:57:06.246255 : CONSUMER (Test:2 Id:C11)->rabbitmq3 : Connection is closed. Opening new connection
22:57:06.246836 : CONSUMER (Test:2 Id:C18)->rabbitmq3 : Connection is closed. Opening new connection
22:57:06.296447 : CONSUMER (Test:2 Id:C4)->rabbitmq3 : Connecting to rabbitmq2
22:57:06.309131 : PUBLISHER(Test:2 Id:P1)->rabbitmq1 : Attempting to connect to rabbitmq1 192.168.192.2
22:57:06```logs.316961 : CONSUMER (Test:2 Id:C4)->rabbitmq3 : Consuming queue: q1_2 with consumer tag: ctag1.4526e04d4d564172ada4eb9e3f52e05c
22:57:06.317738 : PUBLISHER(Test:2 Id:P1)->rabbitmq1 : Connection opened: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0x7fe4903693c8> params=<URLParameters host=192.168.192.2 port=5672 virtual_host=/ ssl=False>>
22:57:06.318855 : PUBLISHER(Test:2 Id:P1)->rabbitmq1 : Channel opened, publishing to commence
22:57:06.346925 : CONSUMER (Test:2 Id:C11)->rabbitmq3 : Connecting to rabbitmq2
22:57:06.358684 : CONSUMER (Test:2 Id:C18)->rabbitmq3 : Connecting to rabbitmq1
22:57:06.376896 : CONSUMER (Test:2 Id:C11)->rabbitmq3 : Consuming queue: q1_2 with consumer tag: ctag1.edb4af20c7f1424fa8ec04c5b8c84b0a
22:57:06.391812 : CONSUMER (Test:2 Id:C18)->rabbitmq3 : Consuming queue: q1_2 with consumer tag: ctag1.92e99bf3d94745ffbce7e84565eb0054
22:57:06.981646 : CONSUMER (Test:2 Id:C5)->rabbitmq2 : CONSUMER CHANGE FOR SEQUENCE P1A! Last id: C11 New id: C5 Last tag: ctag1.d75bd37e788c45be856bb27684b77f01 New tag: ctag1.f35e34b03ea141ad9368c942a1b60614
22:57:06.981728 : CONSUMER (Test:2 Id:C5)->rabbitmq2 : P1a=507468 Last-acked=507464 JUMP FORWARD 4              [Lag: 6.366346s Sent: 22:57:00.615263]
22:57:07.503015 : PUBLISHER(Test:2 Id:P1)->rabbitmq1 : Pos acks: 510000 Neg acks: 0 Undeliverable: 0 No Acks: 0
22:57:09.040183 : CONSUMER (Test:2 Id:C5)->rabbitmq2 : Sample msg: P1a=510003   
```

Another pattern is that the gap is after the redelivered messages. Example from chaos-mixed_quorom_sac.sh, test 10.

```logs
00:54:45.813456 : TEST RUNNER : STOPPING CONSUMER 3 --------------------------------------
00:54:45.813499 : CONSUMER (Test:10 Id:C3)->rabbitmq1 : Requested to stop. Last msg received: b'2019-04-29 00:54:45.754068|P1a=267013'
00:54:48.920947 : PUBLISHER(Test:10 Id:P1)->rabbitmq1 : Pos acks: 270003 Neg acks: 0 Undeliverable: 0 No Acks: 0
00:54:52.825920 : CONSUMER (Test:10 Id:C3)->rabbitmq1 : Closed connection
00:54:52.826006 : TEST RUNNER : Will execute consumer action in 10 seconds
00:54:54.093370 : PUBLISHER(Test:10 Id:P1)->rabbitmq1 : Pos acks: 275025 Neg acks: 0 Undeliverable: 0 No Acks: 0
00:54:59.291773 : PUBLISHER(Test:10 Id:P1)->rabbitmq1 : Pos acks: 280068 Neg acks: 0 Undeliverable: 0 No Acks: 0
00:55:02.842704 : TEST RUNNER : STOPPING CONSUMER 2 --------------------------------------
00:55:02.842784 : CONSUMER (Test:10 Id:C2)->rabbitmq1 : Requested to stop.
00:55:02.844294 : CONSUMER (Test:10 Id:C2)->rabbitmq1 : Closed connection (stream lost)
00:55:02.844488 : TEST RUNNER : STOPPING CONSUMER 9 --------------------------------------
00:55:02.844525 : CONSUMER (Test:10 Id:C9)->rabbitmq2 : Requested to stop.
00:55:02.844597 : CONSUMER (Test:10 Id:C9)->rabbitmq2 : Failed trying to disconnect. Error: An exception of type AssertionError occurred. Arguments:(1,)
00:55:04.468202 : PUBLISHER(Test:10 Id:P1)->rabbitmq1 : Pos acks: 285016 Neg acks: 0 Undeliverable: 0 No Acks: 0
00:55:09.655787 : PUBLISHER(Test:10 Id:P1)->rabbitmq1 : Pos acks: 290010 Neg acks: 0 Undeliverable: 0 No Acks: 0
00:55:14.872943 : PUBLISHER(Test:10 Id:P1)->rabbitmq1 : Pos acks: 295000 Neg acks: 0 Undeliverable: 0 No Acks: 0
00:55:17.845000 : TEST RUNNER : STOPPING CONSUMER 12 --------------------------------------
00:55:17.845087 : CONSUMER (Test:10 Id:C12)->rabbitmq2 : Requested to stop.
00:55:20.046621 : PUBLISHER(Test:10 Id:P1)->rabbitmq1 : Pos acks: 300001 Neg acks: 0 Undeliverable: 0 No Acks: 0
00:55:24.152059 : TEST RUNNER : Test at 5 minute mark, 5 minutes left
00:55:25.220988 : PUBLISHER(Test:10 Id:P1)->rabbitmq1 : Pos acks: 305003 Neg acks: 0 Undeliverable: 0 No Acks: 0
00:55:25.318871 : CONSUMER (Test:10 Id:C13)->rabbitmq1 : CONSUMER CHANGE FOR SEQUENCE P1A! Last id: C3 New id: C13 Last tag: ctag1.76a9068dbb764eee9908ba9394ff58fd New tag: ctag1.7b03f769a8a24f8d81a74b19e21ffa89
00:55:25.318943 : CONSUMER (Test:10 Id:C13)->rabbitmq1 : P1a=267014  REDELIVERED            [Lag: 39.564735s Sent: 00:54:45.754102]
00:55:25.318990 : CONSUMER (Test:10 Id:C13)->rabbitmq1 : P1a=267015  REDELIVERED            [Lag: 39.564844s Sent: 00:54:45.754135]
00:55:25.319028 : CONSUMER (Test:10 Id:C13)->rabbitmq1 : P1a=267016  REDELIVERED            [Lag: 39.564852s Sent: 00:54:45.754167]
00:55:25.319059 : CONSUMER (Test:10 Id:C13)->rabbitmq1 : P1a=267017  REDELIVERED            [Lag: 39.56485s Sent: 00:54:45.754200]
00:55:25.319088 : CONSUMER (Test:10 Id:C13)->rabbitmq1 : P1a=267018  REDELIVERED            [Lag: 39.564844s Sent: 00:54:45.754236]
00:55:25.319124 : CONSUMER (Test:10 Id:C13)->rabbitmq1 : P1a=267019  REDELIVERED            [Lag: 39.564846s Sent: 00:54:45.754269]
00:55:25.319156 : CONSUMER (Test:10 Id:C13)->rabbitmq1 : P1a=267020  REDELIVERED            [Lag: 39.564846s Sent: 00:54:45.754302]
00:55:25.319222 : CONSUMER (Test:10 Id:C13)->rabbitmq1 : P1a=267021  REDELIVERED            [Lag: 39.564877s Sent: 00:54:45.754335]
00:55:25.319277 : CONSUMER (Test:10 Id:C13)->rabbitmq1 : P1a=267022  REDELIVERED            [Lag: 39.564898s Sent: 00:54:45.754368]
00:55:25.319336 : CONSUMER (Test:10 Id:C13)->rabbitmq1 : P1a=267023  REDELIVERED            [Lag: 39.564925s Sent: 00:54:45.754400]
00:55:25.319391 : CONSUMER (Test:10 Id:C13)->rabbitmq1 : P1a=267034 Last-acked=267023 JUMP FORWARD 11              [Lag: 39.564575s Sent: 00:54:45.754806]
00:55:27.381629 : CONSUMER (Test:10 Id:C13)->rabbitmq1 : Sample msg: P1a=270010              [Lag: 38.515112s Sent: 00:54:48.866508]
00:55:29.484732 : CONSUMER (Test:10 Id:C13)->rabbitmq1 : Sample msg: P1a=275010              [Lag: 35.434835s Sent: 00:54:54.049890]
```

#### Consumers unable to consume quorum queue

During and after a network partition was healed, consumers could not connect. Publishers were able to publish though. Test 12 of chaos-mixed_quorom_sac.sh.

Broker 2 shutdown (pause_minority) and in broker logs of rabbitmq1 and 3, many cases of:

```logs
2019-04-28 23:28:37.652 [error] <0.1829.0> Error on AMQP connection <0.1829.0> (172.25.0.1:43704 -> 172.25.0.2:5672, vhost: '/', user: 'jack', state: running), channel 1:

 {{badmatch,{timeout,{'%2F_q1_12',rabbit"rabbitmq2}}},

  [{rabbit_quorum_queue,basic_consume,10,

                         [{file,@src/rabbit_quorum_queue.erl@},{line,502}]},

                           {rabbit_amqqueue,basic_consume,12,

                                              [{file,@src/rabbit_amqqueue.erl@},{line,1412}]},

                                                {rabbit_channel,'-basic_consume/8-fun-0-',10,

                                                                  [{file,@src/rabbit_channel.erl@},{line,1701}]},

                                                                    {rabbit_misc,with_exit_handler,2,[{file,@src/rabbit_misc.erl@},{line,480}]},

                                                                      {rabbit_channel,basic_consume,8,

                                                                                        [{file,@src/rabbit_channel.erl@},{line,1698}]},

                                                                                          {rabbit_channel,handle_method,3,

                                                                                                            [{file,@src/rabbit_channel.erl@},{line,1402}]},

                                                                                                              {rabbit_channel,handle_cast,2,[{file,@src/rabbit_channel.erl@},{line,602}]},

                                                                                                                {gen_server2,handle_msg,2,[{file,@src/gen_server2.erl@},{line,1050}]}]}
```

### chaos-cons-only_quorum_sac_high_prefetch.sh saw message loss with quorum queues and SAC

Test log and broker logs can be downloaded from here: https://s3-eu-west-1.amazonaws.com/vanlightly-rabbitmq-tests/20190429/chaos-cons-only_quorum_sac_high_prefetch_20190428_2223.zip

#### On consumer change, gap in messages
Prefetch of 1000.

Example from test 1. After redelivered messages, a gap. Also see test 14.

```logs
22:41:59.663581 : TEST RUNNER : STOPPING CONSUMER 2 --------------------------------------
22:41:59.663635 : CONSUMER (Test:1 Id:C2)->rabbitmq3 : Requested to stop. Last msg received: b'2019-04-28 22:41:59.480619|P1a=331503'
22:41:59.682978 : CONSUMER (Test:1 Id:C4)->rabbitmq2 : Consuming queue: q1_1 with consumer tag: ctag1.bee663ad05cd437e81ea97f5d3009bd0
22:41:59.700116 : CONSUMER (Test:1 Id:C2)->rabbitmq3 : Failed trying to disconnect. Error: An exception of type AssertionError occurred. Arguments:(('_AsyncTransportBase._initate_abort() expected non-_STATE_COMPLETED', 4),)
22:41:59.700676 : TEST RUNNER : Will execute consumer action in 10 seconds
22:41:59.899638 : CONSUMER (Test:1 Id:C4)->rabbitmq2 : CONSUMER CHANGE FOR SEQUENCE P1A! Last id: C2 New id: C4 Last tag: ctag1.43b3b29515de414482b82dab2d3510e7 New tag: ctag1.bee663ad05cd437e81ea97f5d3009bd0
22:41:59.899704 : CONSUMER (Test:1 Id:C4)->rabbitmq2 : P1a=331504  REDELIVERED            [Lag: 0.418977s Sent: 22:41:59.480652]
22:41:59.899742 : CONSUMER (Test:1 Id:C4)->rabbitmq2 : P1a=331505  REDELIVERED            [Lag: 0.419049s Sent: 22:41:59.480685]
22:41:59.899768 : CONSUMER (Test:1 Id:C4)->rabbitmq2 : P1a=331506  REDELIVERED            [Lag: 0.419043s Sent: 22:41:59.480718]
22:41:59.899793 : CONSUMER (Test:1 Id:C4)->rabbitmq2 : P1a=331507  REDELIVERED            [Lag: 0.419036s Sent: 22:41:59.480751]
22:41:59.899819 : CONSUMER (Test:1 Id:C4)->rabbitmq2 : P1a=331508  REDELIVERED            [Lag: 0.419027s Sent: 22:41:59.480785]
22:41:59.899844 : CONSUMER (Test:1 Id:C4)->rabbitmq2 : P1a=331509  REDELIVERED            [Lag: 0.41902s Sent: 22:41:59.480818]
22:41:59.899924 : CONSUMER (Test:1 Id:C4)->rabbitmq2 : P1a=331510  REDELIVERED            [Lag: 0.419061s Sent: 22:41:59.480853]
... omitted for brevity
22:41:59.909562 : CONSUMER (Test:1 Id:C4)->rabbitmq2 : P1a=331710  REDELIVERED            [Lag: 0.420785s Sent: 22:41:59.488770]
22:41:59.909612 : CONSUMER (Test:1 Id:C4)->rabbitmq2 : P1a=331711  REDELIVERED            [Lag: 0.420798s Sent: 22:41:59.488803]
22:41:59.909642 : CONSUMER (Test:1 Id:C4)->rabbitmq2 : P1a=331712  REDELIVERED            [Lag: 0.420799s Sent: 22:41:59.488836]
22:41:59.909667 : CONSUMER (Test:1 Id:C4)->rabbitmq2 : P1a=331713  REDELIVERED            [Lag: 0.420792s Sent: 22:41:59.488868]
22:41:59.909693 : CONSUMER (Test:1 Id:C4)->rabbitmq2 : P1a=331714  REDELIVERED            [Lag: 0.420786s Sent: 22:41:59.488900]
22:41:59.909718 : CONSUMER (Test:1 Id:C4)->rabbitmq2 : P1a=331715  REDELIVERED            [Lag: 0.420778s Sent: 22:41:59.488933]
22:41:59.909744 : CONSUMER (Test:1 Id:C4)->rabbitmq2 : P1a=331716  REDELIVERED            [Lag: 0.420772s Sent: 22:41:59.488965]
22:41:59.909769 : CONSUMER (Test:1 Id:C4)->rabbitmq2 : P1a=331717  REDELIVERED            [Lag: 0.420765s Sent: 22:41:59.488997]
22:41:59.909795 : CONSUMER (Test:1 Id:C4)->rabbitmq2 : P1a=331718  REDELIVERED            [Lag: 0.420757s Sent: 22:41:59.489030]
22:42:00.911502 : CONSUMER (Test:1 Id:C4)->rabbitmq2 : P1a=332001 Last-acked=331718 JUMP FORWARD 283              [Lag: 0.411707s Sent: 22:42:00.499745]
22:42:02.723762 : PUBLISHER(Test:1 Id:P1)->rabbitmq2 : Pos acks: 335000 Neg acks: 0 Undeliverable: 0 No Acks: 0
```

#### Jumping forwards and backwards with redelivered, leaves gap

In this example from test 3, the messages 251264 to 251312 were lost. Other examples include another in test 3, test 10, test 14.

```logs
23:09:12.085001 : TEST RUNNER : STOPPING CONSUMER 3 --------------------------------------
23:09:12.085075 : CONSUMER (Test:3 Id:C3)->rabbitmq1 : Requested to stop. Last msg received: b'2019-04-28 23:09:11.988117|P1a=251186'
23:09:12.152787 : CONSUMER (Test:3 Id:C3)->rabbitmq1 : Closed connection (stream lost)
23:09:12.152852 : TEST RUNNER : STOPPING CONSUMER 5 --------------------------------------
23:09:12.152862 : CONSUMER (Test:3 Id:C5)->rabbitmq3 : Requested to stop.
23:09:12.154178 : CONSUMER (Test:3 Id:C5)->rabbitmq3 : Closed connection (stream lost)
23:09:12.154500 : TEST RUNNER : Will execute consumer action in 10 seconds
23:09:13.118845 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : CONSUMER CHANGE FOR SEQUENCE P1A! Last id: C3 New id: C1 Last tag: ctag1.4d448698b3f14c04ba058a6c02fdc710 New tag: ctag1.3210f04ad60044f78e1b9efafb697392
23:09:13.118890 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251635 Last-acked=251186 JUMP FORWARD 449              [Lag: 1.114743s Sent: 23:09:12.004074]
23:09:13.128345 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251257 Last-acked=252000 JUMP BACK 743  REDELIVERED            [Lag: 1.137664s Sent: 23:09:11.990671]
23:09:13.135017 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251258  REDELIVERED            [Lag: 1.144281s Sent: 23:09:11.990707]
23:09:13.135098 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251259  REDELIVERED            [Lag: 1.144347s Sent: 23:09:11.990741]
23:09:13.136736 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251260  REDELIVERED            [Lag: 1.145936s Sent: 23:09:11.990774]
23:09:13.137928 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251261  REDELIVERED            [Lag: 1.14601s Sent: 23:09:11.990807]
23:09:13.138030 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251262  REDELIVERED            [Lag: 1.147178s Sent: 23:09:11.990841]
23:09:13.138063 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251263  REDELIVERED            [Lag: 1.14718s Sent: 23:09:11.990876]
23:09:13.138092 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251313 Last-acked=251263 JUMP FORWARD 50  REDELIVERED            [Lag: 1.145463s Sent: 23:09:11.992621]
23:09:13.138161 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251314  REDELIVERED            [Lag: 1.145498s Sent: 23:09:11.992654]
23:09:13.138220 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251315  REDELIVERED            [Lag: 1.145523s Sent: 23:09:11.992689]
23:09:13.138271 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251316  REDELIVERED            [Lag: 1.14554s Sent: 23:09:11.992723]
23:09:13.138323 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251317  REDELIVERED            [Lag: 1.145558s Sent: 23:09:11.992757]
23:09:13.138375 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251318  REDELIVERED            [Lag: 1.145577s Sent: 23:09:11.992790]
23:09:13.138426 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251319  REDELIVERED            [Lag: 1.145595s Sent: 23:09:11.992823]
23:09:13.138478 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251320  REDELIVERED            [Lag: 1.14559s Sent: 23:09:11.992880]
23:09:13.138530 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251321  REDELIVERED            [Lag: 1.145598s Sent: 23:09:11.992924]
... omitted for brevity
23:09:13.160155 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251627  REDELIVERED            [Lag: 1.156345s Sent: 23:09:12.003804]
23:09:13.160181 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251628  REDELIVERED            [Lag: 1.156337s Sent: 23:09:12.003837]
23:09:13.160241 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251629  REDELIVERED            [Lag: 1.156362s Sent: 23:09:12.003871]
23:09:13.160271 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251630  REDELIVERED            [Lag: 1.15636s Sent: 23:09:12.003904]
23:09:13.160296 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251631  REDELIVERED            [Lag: 1.15635s Sent: 23:09:12.003940]
23:09:13.160358 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251632  REDELIVERED            [Lag: 1.156375s Sent: 23:09:12.003974]
23:09:13.160390 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251633  REDELIVERED            [Lag: 1.156377s Sent: 23:09:12.004007]
23:09:13.160415 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251634  REDELIVERED            [Lag: 1.156369s Sent: 23:09:12.004040]
23:09:13.160441 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251187 Last-acked=251634 JUMP BACK 447  REDELIVERED            [Lag: 1.172284s Sent: 23:09:11.988150]
23:09:13.160467 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251188  REDELIVERED            [Lag: 1.172277s Sent: 23:09:11.988184]
23:09:13.160493 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251189  REDELIVERED            [Lag: 1.172269s Sent: 23:09:11.988217]
23:09:13.160519 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251190  REDELIVERED            [Lag: 1.172262s Sent: 23:09:11.988251]
23:09:13.160544 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251191  REDELIVERED            [Lag: 1.172254s Sent: 23:09:11.988284]
23:09:13.160569 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251192  REDELIVERED            [Lag: 1.172222s Sent: 23:09:11.988341]
23:09:13.160594 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251193  REDELIVERED            [Lag: 1.172211s Sent: 23:09:11.988377]
23:09:13.160619 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251194  REDELIVERED            [Lag: 1.172203s Sent: 23:09:11.988410]
... omitted for brevity
23:09:13.169949 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251250  REDELIVERED            [Lag: 1.179566s Sent: 23:09:11.990375]
23:09:13.170011 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251251  REDELIVERED            [Lag: 1.179594s Sent: 23:09:11.990408]
23:09:13.170061 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251252  REDELIVERED            [Lag: 1.179612s Sent: 23:09:11.990441]
23:09:13.170109 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251253  REDELIVERED            [Lag: 1.179628s Sent: 23:09:11.990474]
23:09:13.170158 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251254  REDELIVERED            [Lag: 1.179643s Sent: 23:09:11.990508]
23:09:13.170206 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251255  REDELIVERED            [Lag: 1.179658s Sent: 23:09:11.990541]
23:09:13.170236 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=251256  REDELIVERED            [Lag: 1.179655s Sent: 23:09:11.990575]
23:09:13.170262 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : P1a=252001 Last-acked=251256 JUMP FORWARD 745              [Lag: 0.151107s Sent: 23:09:13.019147]
23:09:15.310749 : PUBLISHER(Test:3 Id:P1)->rabbitmq3 : Pos acks: 255000 Neg acks: 0 Undeliverable: 0 No Acks: 0
23:09:16.257787 : CONSUMER (Test:3 Id:C1)->rabbitmq3 : Sample msg: P1a=255049              [Lag: 0.111584s Sent: 23:09:16.146193]
```

### Mirrored queues

Passed tests.

Test logs here:

- https://s3-eu-west-1.amazonaws.com/vanlightly-rabbitmq-tests/20190429/chaos-cons-only_mirrored_sac_high_prefetch_20190428_2226.zip
- https://s3-eu-west-1.amazonaws.com/vanlightly-rabbitmq-tests/20190429/chaos-mixed_mirrored_sac_20190428_2219.zip