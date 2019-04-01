#! /bin/bash

python -u quorum-queue-test.py \
--queue $1 \
--tests 20 \
--actions 20 \ 
--grace-period-sec 300 \
--in-flight-max 200 \
--chaos mixed \
--chaos-min-interval 30
--chaos-max-interval 120
--sac true 2>&1 | tee ../../logs/$1.log