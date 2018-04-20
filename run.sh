#!/usr/bin/env bash

nodeName=$1

python3.5 link_layer.py ${nodeName} &
python3.5 network_layer.py ${nodeName} &
python3.5 application_layer.py ${nodeName}