#! /bin/bash
# Get resources used on a particular host.

curl -X POST http://10.8.0.42:5000/api/resources -H "Content-Type: application/json" -d '{"hosts": ["perchost.bjd2385.com"]}' | jq
