#! /bin/bash

cd ../..

python -u random-test.py --queue $1 \
--tests 1 \
--run-minutes 10 \
--grace-period-sec 300 \
--in-flight-max 200 \
--print-mod 1000 \
--sequences 1 \
--cluster 3 \
--publishers 1 \
--consumers 3 \
--queue-type quorum \
--chaos-actions true \
--chaos-mode mixed \
--chaos-min-interval 30 \
--chaos-min-interval 90 \
--consumer-actions true \
--consumer-min-interval 10 \
--consumer-max-interval 45 \
--sac true \
--new-cluster true