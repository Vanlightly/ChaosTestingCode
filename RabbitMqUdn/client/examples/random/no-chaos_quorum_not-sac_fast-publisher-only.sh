#! /bin/bash

cd ../..

python -u random-test.py --queue $1 \
--tests 1 \
--run-minutes 10 \
--grace-period-sec 300 \
--in-flight-max 20000 \
--print-mod 20000 \
--sequences 1 \
--cluster 3 \
--consumers 0 \
--queue-type quorum \
--chaos-actions false \
--consumer-actions false \
--sac false \
--new-cluster false