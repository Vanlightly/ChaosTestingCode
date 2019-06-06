#!/bin/bash

#$1 ip
#$2 Consumer number
#$3 Broker number

LT=9
if [ $2 > $LT ]; then
    ZEROS="00"
else
    ZEROS="000"
fi

for ((B=1; B<=$3; B++))
do
    # curl -w "%{http_code} " -d '{"name":"C'"$2"'_R'"$B"'","listen":"0.0.0.0:'"$B$ZEROS$2"'","upstream":"rabbitmq'"$B"':5672","enabled":true}' -H "Content-Type: application/json" -X POST  http://$1:8474/proxies/C$2_R$B
    curl_status=$(curl -s -o /dev/null -w "%{http_code}" -d '{"name":"C'"$2"'_R'"$B"'","listen":"0.0.0.0:'"$B$ZEROS$2"'","upstream":"rabbitmq'"$B"':5672","enabled":true}' -H "Content-Type: application/json" -X POST  http://$1:8474/proxies/C$2_R$B)

    if [[ $curl_status != "200" ]]; then
        echo "Failed to enabled proxy for consumer $2 for rabbitmq$B"
    fi
done
#echo "Enabled proxies for consumer $2"
