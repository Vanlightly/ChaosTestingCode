#! /bin/bash

python -u random-test.py --queue $1 \
--tests 1 \
--run-minutes 10 \
--grace-period-sec 300 \
--in-flight-max 20000 \
--print-mod 1000 \
--sequences 1 \
--cluster 3 \
--consumers 0 \
--queue-type mirrored \
--chaos-actions false \
--consumer-actions false \
--sac true \
--new-cluster false