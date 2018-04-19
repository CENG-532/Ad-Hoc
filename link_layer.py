import zmq
import time
import sys
import socket
import threading
import pickle
import queue

from math import sqrt, pow
from collections import namedtuple


# have MAC layout to match ip to mac or use IP right away.

server_message_queue = queue.Queue()  # queue holds raw values of messages in byte format.

position_self = (3, 4)  # some position

communication_range = 10

node_id = 10

packet = namedtuple("packet", ["type", "source", "destination", "next_hop", "position", "message"])

network_layer_down_stream_address = "tcp://network_layer:5556"

link_layer_up_stream_address = "tcp://link_layer:5554"


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
    client_socket.connect(network_layer_down_stream_address)

    while True:
        message = server_message_queue.get()
        message = pickle.loads(message)

        if is_in_range(message.Position):
            client_socket.send(message)


def network_layer_listener(context):
    server_socket = context.socket(zmq.REP)
    server_socket.bind(link_layer_up_stream_address)
    udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        # to send a message, you need to receive a structure from network layer
        message_raw = server_socket.recv()
        message = pickle.loads(message_raw)
        # depending on the message command, which can be decided after a discussion, we can define set of commands.
        ip = get_ip(message)

        udp_client.send(ip, message_raw)


def link_layer_listener(context, address):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.setblocking(0)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(address)

    worker_thread = threading.Thread(target=worker_listener, args=(context,))
    worker_thread.start()

    while True:
        message = server_socket.recv(1024)

        server_message_queue.put(message)

    worker_thread.join()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Arguments are not valid. Usage: Pos.x Pos.y")
        exit(-1)

    position_self = (sys.argv[1], sys.argv[2])


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
