#!/bin/bash

# $1 topic
# $2 ensemble size
# $3 write quorum size
# $4 ack quorum size

bash create-tenant.sh pulsar1 vanlightly
bash create-namespace-with-retention.sh pulsar1 vanlightly ns1 $1 $2 $3