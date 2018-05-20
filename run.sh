#!/usr/bin/env bash

nodeName=$1

python3 link_layer.py ${nodeName} &
python3 network_layer.py ${nodeName} &
python3 application_layer.py ${nodeName} &

