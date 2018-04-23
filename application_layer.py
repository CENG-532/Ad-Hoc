import zmq
import threading
import pickle
import signal
import sys
import configparser

from collections import namedtuple

packet = namedtuple("packet",
                    ["type", "source", "name", "sequence", "link_state", "destination", "next_hop",
                     "position",
                     "message"])
application_layer_address = "tcp://127.0.0.1:5557"  # application layer address
network_layer_up_stream_address = "tcp://127.0.0.1:5555"  # network layer up stream


def get_message_to_send(context):
    client_socket = context.socket(zmq.PUSH)
    client_socket.connect(network_layer_up_stream_address)
    # get a message from user and send it
    # commit
    while True:
        message = input("message: ")
        destination = input("destination: ")

        packet_to_send = packet("DATA", "", "", "", {}, destination, "", "", message)
        client_socket.send(pickle.dumps(packet_to_send))


def signal_handler(signal, frame):
    context.term()
    context.destroy()
    sys.exit()


def read_config_file(filename, name):
    global application_layer_address, network_layer_up_stream_address
    config = configparser.ConfigParser()
    config.read(filename)

    node_settings = config[name]
    application_layer_address = node_settings["application_layer_address"]
    network_layer_up_stream_address = node_settings["network_layer_up_stream_address"]


if __name__ == "__main__":
    context = zmq.Context()
    signal.signal(signal.SIGINT, signal_handler)

    read_config_file("config.ini", sys.argv[1])

    server_socket = context.socket(zmq.PULL)
    server_socket.bind(application_layer_address)
    server_socket.setsockopt(zmq.LINGER, 0)

    send_thread = threading.Thread(target=get_message_to_send, args=(context,))
    send_thread.start()

    while True:
        received_message = server_socket.recv()
        # process received message here
        print(pickle.loads(received_message))
        # break on some condition

    send_thread.join()
