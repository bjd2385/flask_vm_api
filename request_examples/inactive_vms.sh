#! /bin/bash
# List active agents

curl -X POST http://10.8.0.42:5000/api/list -H "Content-Type: application/json" -d '{"hosts":["perchost.bjd2385.com","b350-gaming-pc.bjd2385.com","routerhost.bjd2385.com"],"status":"inactive"}' | jq
