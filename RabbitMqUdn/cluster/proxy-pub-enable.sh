#!/bin/bash

#$1 Consumer number
#$2 Broker number

for B in {1..3}
do
    curl -s -o /dev/null -w "%{http_code}" -d '{"name":"P1R'"$B"'","listen":"0.0.0.0:'"$B"'000'"$2"'","upstream":"rabbitmq'"$B"':5672","enabled":true}' -H "Content-Type: application/json" -X POST  http://$1:8474/proxies
    echo " - Enabled proxy for publishers for rabbitmq$B"
done
