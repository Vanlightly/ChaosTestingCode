#!/bin/bash

for ((B=1; B<=$2; B++))
do
    curl -s -o /dev/null -w "%{http_code}" -d '{"name":"P1R'"$B"'","listen":"0.0.0.0:'"$B"'0000","upstream":"rabbitmq'"$B"':5672"}' -H "Content-Type: application/json" -X POST  http://$1:8474/proxies
    echo " - Created proxy for publisher for rabbitmq$B"
done

for C in {1..9}
do
    for ((B=1; B<=$2; B++))
    do
        curl -s -o /dev/null -w "%{http_code}" -d '{"name":"C'"$C"'_R'"$B"'","listen":"0.0.0.0:'"$B"'000'"$C"'","upstream":"rabbitmq'"$B"':5672"}' -H "Content-Type: application/json" -X POST  http://$1:8474/proxies
        echo " - Created proxy for consumer $C for rabbitmq$B"
    done
done

for C in {10..20}
do
    for ((B=1; B<=$2; B++))
    do
        curl -s -o /dev/null -w "%{http_code}" -d '{"name":"C'"$C"'_R'"$B"'","listen":"0.0.0.0:'"$B"'00'"$C"'","upstream":"rabbitmq'"$B"':5672"}' -H "Content-Type: application/json" -X POST  http://$1:8474/proxies
        echo " - Created proxy for  consumer $C for rabbitmq$B"
    done
done



