#! /bin/bash

cd ../..

python publish-consume.py \
--new-cluster true \
--cluster-size 3 \
--rmq-version 3.8 \
--queue $1 \
--queue-type quorum \
--qq-max-length 1000 \
--msgs 10000000 \
--pub-mode direct \
--msg-mode large-msgs \
--msg-length 10000 \
--consumers 0

