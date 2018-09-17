#!/bin/bash

python co-producer.py $1 $2 $3 $4 1  &
sleep 0.1
python co-producer.py $1 $2 $3 $4 2  &
sleep 0.1
python co-producer.py $1 $2 $3 $4 3  &
sleep 0.1
python co-producer.py $1 $2 $3 $4 4  &
sleep 0.1
python co-producer.py $1 $2 $3 $4 5  &
sleep 0.1
python co-producer.py $1 $2 $3 $4 6  &
sleep 0.1
python co-producer.py $1 $2 $3 $4 7  &
sleep 0.1
python co-producer.py $1 $2 $3 $4 8  &
sleep 0.1
python co-producer.py $1 $2 $3 $4 9  &
sleep 0.1
python co-producer.py $1 $2 $3 $4 10 &

wait $(jobs -p)
echo "Runs complete"