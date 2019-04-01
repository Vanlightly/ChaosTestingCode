#! /bin/bash

cd ../..

python -u random-test.py --queue $1 \
--tests 1 \
--run-minutes 10 \
--grace-period-sec 300 \
--in-flight-max 200 \
--sequences 1 \
--cluster 3 \
--consumers 2 \
--queue-type quorum \
--chaos-actions false \
--consumer-actions true \
--consumer-min-interval 10 \
--consumer-max-interval 10 \
--sac true \
--new-cluster false