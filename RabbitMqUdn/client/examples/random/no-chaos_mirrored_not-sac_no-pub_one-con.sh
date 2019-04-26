#! /bin/bash

cd ../..

TEST_NAME=$(date +%Y%m%d_%H%M)

python -u random-test.py --queue $1 \
--test-name $TEST_NAME \
--tests 1 \
--run-minutes 10 \
--grace-period-sec 300 \
--in-flight-max 200 \
--print-mod 1000 \
--sequences 1 \
--cluster 3 \
--publishers 0 \
--consumers 1 \
--queue-type mirrored \
--chaos-actions false \
--consumer-actions false \
--sac false \
--new-cluster false