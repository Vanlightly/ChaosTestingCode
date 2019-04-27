#! /bin/bash

cd ../..

TEST_NAME=$(date +%Y%m%d_%H%M)
mkdir logs/$TEST_NAME

python -u random-test.py --queue $1 \
--test-name $TEST_NAME \
--tests 20 \
--run-minutes 10 \
--grace-period-sec 300 \
--in-flight-max 1000 \
--sequences 1 \
--cluster 3 \
--publishers 1 \
--consumers 20 \
--queue-type quorum \
--chaos-actions true \
--chaos-mode mixed \
--chaos-min-interval 30 \
--chaos-min-interval 90 \
--consumer-actions true \
--consumer-min-interval 10 \
--consumer-max-interval 45 \
--sac true \
--new-cluster true 2>&1 | tee logs/$TEST_NAME/test_run.log