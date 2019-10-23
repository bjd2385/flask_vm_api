#! /bin/bash
# Get the XML for VMs on some host. You can specify multiple VMs, but they must
# all be on the same host.

curl -X POST http://10.8.0.42:5000/api/xml -H "Content-Type: application/json" -d '{"host":"perchost.bjd2385.com","guests":["Windows10","DC2"]}' | jq
