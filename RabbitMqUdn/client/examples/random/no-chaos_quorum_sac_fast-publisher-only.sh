#! /bin/bash

cd ../..

TEST_NAME=$(date +%Y%m%d_%H%M)

python -u random-test.py --queue $1 \
--test-name $TEST_NAME \
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
--sac true \
--new-cluster false 2>&1 | tee logs/$TEST_NAME/test_run.log