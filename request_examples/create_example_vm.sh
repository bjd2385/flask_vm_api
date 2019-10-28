#! /bin/bash
# Create a VM.

curl -X POST http://10.8.0.42:5000/api/create -H "Content-Type: application/json" -d '{"host":"perchost.bjd2385.com","guestName":"test_1","ipAddress":"192.168.1.156","datasetName":"VMPool/test_1","sourceSnapshot":"VMPool/images/ubuntu_16_net-grub@base-mi-no-iface-rename-grub","bridge":"br0"}'
