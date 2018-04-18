import zmq
import time
import socket
import threading
import pickle
import queue

from math import sqrt, pow
from collections import namedtuple


# have MAC layout to match ip to mac or use IP right away.

server_message_queue = queue.Queue()

position_self = (3, 4)  # some position

communication_range = 10

node_id = 10

packet = namedtuple("packet", ["type", "source", "destination", "next_hop", "position", "message"])


def get_ip(message):
    # we need both port numbers and IP addresses of destination.
    return message.next_hop


def update_mac_table(message):
    # here we might want to update mac table if we decide to use different convention than IP addressing.
    pass


def calculate_distance(position):
    return sqrt(pow(position[0] - position_self[0], 2) + pow(position[1] - position_self[1], 2))


def is_in_range(message):
    # here we need to set our distance to something, and compare it with the received message.
    # omit the message if it is not in our range.
    return calculate_distance(message.position) <= communication_range


def worker_listener(context):
    client_socket = context.socket(zmq.REQ)

    while True:
        message = server_message_queue.get()
        message = pickle.loads(message)

        if is_in_range(message.Position):
            client_socket.send("tcp://network_layer:5556", message)


def network_layer_listener(context, address):
    server_socket = context.socket(zmq.REP)
    server_socket.bind(address)
    udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        # to send a message, you need to receive a structure from network layer
        message = server_socket.recv()
        # depending on the message command, which can be decided after a discussion, we can define set of commands.
        ip = get_ip(message)

        udp_client.send(ip, message)


def link_layer_listener(context, address):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.setblocking(0)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(address)

    thread = threading.Thread(target=worker_listener, args=(context,))
    thread.start()

    while True:
        message = server_socket.recv(1024)

        server_message_queue.put(message)

    thread.join()

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
