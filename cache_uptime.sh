#! /bin/bash
# Reach out to my domains and cache their load averages to file. Goal is to make the
# resulting format as close to Python dict as possible from the outset. This needs to
# be a cronjob, of course - otherwise these values never update :shrug:

domains=(
    "perchost.bjd2385.com"
    "routerhost.bjd2385.com"
    "b350-gaming-pc.bjd2385.com"
)

cachefile="/tmp/uptime.cache"

truncate -s 0 "$cachefile"

echo "{" >> "$cachefile"

for dom in ${domains[@]}
do
    if [ "$dom" = "$(hostname)" ]
    then
        # No need for SSH.
        echo "\"${dom}\":\"$(uptime | grep -oP "load average: \K.*")\"," >> "$cachefile"
    else
        # We need to have SSH access to acquire the uptime.
        echo "\"${dom}\":\"$(ssh "$dom" uptime | grep -oP "load average: \K.*")\"," >> "$cachefile"
    fi
done

echo "}" >> "$cachefile"
