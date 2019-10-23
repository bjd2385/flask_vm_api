#! /bin/bash
# Reach out to my domains and cache their load averages to file.

domains=(
    "perchost.bjd2385.com"
    "routerhost.bjd2385.com"
)

> /tmp/uptime.cache

for dom in ${domains[@]}
do
    echo "${dom}:$(ssh "$dom" uptime | grep -oP "load average: \K.*")" >> /tmp/uptime.cache
done

echo "b350-gaming-pc.bjd2385.com:$(uptime | grep -oP "load average: \K.*")" >> /tmp/uptime.cache
