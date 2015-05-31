#!/bin/bash

curl -X POST -d '{"dpid": 218473257898053,"cookie": 1,"idle_timeout": 5,"match":{"in_port":1},"actions":[{"type":"OUTPUT","port": 2}]}' http://localhost:8080/stats/flowentry/add

curl -X POST -d '{"dpid": 218473257898053,"cookie": 1,"idle_timeout": 5,"match":{"in_port":2},"actions":[{"type":"OUTPUT","port": 1}]}' http://localhost:8080/stats/flowentry/add

curl -X POST -d '{"dpid": 173897297146441,"cookie": 1,"idle_timeout": 5,"match":{"in_port":1},"actions":[{"type":"OUTPUT","port": 2}]}' http://localhost:8080/stats/flowentry/add

curl -X POST -d '{"dpid": 173897297146441,"cookie": 1,"idle_timeout": 5,"match":{"in_port":2},"actions":[{"type":"OUTPUT","port": 1}]}' http://localhost:8080/stats/flowentry/add
