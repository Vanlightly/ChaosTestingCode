#!/bin/bash

python co-producer.py $1 $2 $3 $4 1 &> file1.out &
sleep 0.1
python co-producer.py $1 $2 $3 $4 2 &> file2.out &
sleep 0.1
python co-producer.py $1 $2 $3 $4 3 &> file3.out &
sleep 0.1
python co-producer.py $1 $2 $3 $4 4 &> file4.out &
sleep 0.1
python co-producer.py $1 $2 $3 $4 5 &> file5.out &
sleep 0.1
python co-producer.py $1 $2 $3 $4 6 &> file6.out &
sleep 0.1
python co-producer.py $1 $2 $3 $4 7 &> file7.out &
sleep 0.1
python co-producer.py $1 $2 $3 $4 8 &> file8.out &
sleep 0.1
python co-producer.py $1 $2 $3 $4 9 &> file9.out &
sleep 0.1
python co-producer.py $1 $2 $3 $4 10 &> file10.out &

wait $(jobs -p)
echo "Runs complete"

#LINE1=$(cat file1.out | grep RUN_ID | awk '{ print $5 }')
ACK_TOTAL=$(( $(cat file1.out | grep Sent: | awk '{ print $7 }') \
    + $(cat file2.out | grep Sent: | awk '{ print $7 }') \
    + $(cat file3.out | grep Sent: | awk '{ print $7 }') \
    + $(cat file4.out | grep Sent: | awk '{ print $7 }') \
    + $(cat file5.out | grep Sent: | awk '{ print $7 }') \
    + $(cat file6.out | grep Sent: | awk '{ print $7 }') \
    + $(cat file7.out | grep Sent: | awk '{ print $7 }') \
    + $(cat file8.out | grep Sent: | awk '{ print $7 }') \
    + $(cat file9.out | grep Sent: | awk '{ print $7 }') \
    + $(cat file10.out | grep Sent: | awk '{ print $7 }') \
 ))
echo Acknowledged total: $ACK_TOTAL