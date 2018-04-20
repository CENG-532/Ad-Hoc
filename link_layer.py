import zmq
import time
import sys
import socket
import threading
import pickle
import queue
import configparser

from math import sqrt, pow
from collections import namedtuple


# have MAC layout to match ip to mac or use IP right away.

server_message_queue = queue.Queue()  # queue holds raw values of messages in byte format.

position_self = (3, 4)  # some position

communication_range = 10

node_id = 10

packet = namedtuple("packet", ["type", "source", "destination", "next_hop", "position", "message"])

network_layer_down_stream_address = "tcp://127.0.0.1:5556"  # network layer down stream

link_layer_up_stream_address = "tcp://127.0.0.1:5554"  # link layer up stream

ip_address_self = "127.0.0.1:5554"


def get_ip(message):
    # we need both port numbers and IP addresses of destination.
    # return message.next_hop
    # test:
    return "127.0.0.1", 5900

def update_mac_table(message):
    # here we might want to update mac table if we decide to use different convention than IP addressing.
    pass


def calculate_distance(position):
    return sqrt(pow(position[0] - position_self[0], 2) + pow(position[1] - position_self[1], 2))


def is_in_range(position):
    # here we need to set our distance to something, and compare it with the received message.
    # omit the message if it is not in our range.
    return calculate_distance(position) <= communication_range


def worker_listener(context):
    print("worker thread is started.")
    client_socket = context.socket(zmq.PUSH)
    client_socket.connect(network_layer_down_stream_address)

    while True:
        message_raw = server_message_queue.get()
        message = pickle.loads(message_raw)

        if is_in_range(message.position):
            client_socket.send(message_raw)


def network_layer_listener():
    print("network layer listener is started")
    server_socket = context.socket(zmq.PULL)
    server_socket.bind(link_layer_up_stream_address)
    server_socket.setsockopt(zmq.LINGER, 0)

    udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        message_raw = server_socket.recv()
        message = pickle.loads(message_raw)
        # depending on the message command, which can be decided after a discussion, we can define set of commands.
        ip = get_ip(message)
        print(message)
        udp_client.sendto(message_raw, ip)


def link_layer_listener():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(ip_address_self)

    worker_thread = threading.Thread(target=worker_listener, args=(context,))
    worker_thread.start()

    while True:
        message = server_socket.recv(1024)

        server_message_queue.put(message)

    worker_thread.join()


def read_config_file(filename, name):
    global ip_address_self, communication_range, position_self

    config = configparser.ConfigParser()
    config.read(filename)
    node_settings = config[name]
    ip_address_self = node_settings["ip"]
    port_read = ip_address_self.split(":")
    ip_address_self = (port_read[0][1:], int(port_read[1][:-1]))

    print(ip_address_self)

    position_self = (float(node_settings["positionX"]), float(node_settings["positionX"]))
    communication_range = float(config["DEFAULT"]["range"])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Arguments are not valid. Usage: [name of the node]")
        exit(-1)

    context = zmq.Context()

    read_config_file("config.ini", sys.argv[1])

    link_layer_server_thread = threading.Thread(target=link_layer_listener, args=())
    network_layer_listener_thread = threading.Thread(target=network_layer_listener, args=())

    link_layer_server_thread.start()
    network_layer_listener_thread.start()

    link_layer_server_thread.join()
    network_layer_listener_thread.join()

# context = zmq.Context()
#
# socket = context.socket(zmq.REP)
#
# socket.bind("tcp://*:5555")
#
# while True:
#     #  Wait for next request from client
#     message = socket.recv()
#     print("Received request: %s" % message)
#
#     #  Do some 'work'
#     time.sleep(1)
#
#     #  Send reply back to client
#     socket.send(b"World")
