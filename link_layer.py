import zmq
import time
import socket


# have MAC layout to match ip to mac or use IP right away.

def getIP(message):
    # we need both port numbers and IP addresses of destination.
    pass


def calculate_distance(message):
    # here we need to set our distance to something, and compare it with the received message.
    # omit the message if it is not in our range.
    pass


def update_mac_table(message):
    # here we might want to update mac table if we decide to use different convention than IP addressing.
    pass


def network_layer_listener(context, address):
    server_socket = context.socket(zmq.REP)
    server_socket.bind(address)
    udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        # to send a message, you need to receive a structure from network layer
        message = server_socket.recv()
        # depending on the message command, which can be decided after a discussion, we can define set of commands.
        ip = getIP(message)

        udp_client.send(ip, message)

        pass

    pass


def link_layer_listener(context, address):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket = context.socket(zmq.REQ)
    server_socket.bind(address)

    while True:
        message = server_socket.recv()

        ip = getIP(message)  # dunno may not be required

        # do something with it.

        client_socket.send("tcp://network_layer:5556", message)  # or what ever information we have.
    pass


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
