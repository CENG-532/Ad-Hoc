import zmq
import threading
import pickle
import signal
import sys
import configparser
import time
import queue
import election_algorithms

from collections import namedtuple

packet = namedtuple("packet",
                    ["type", "source", "name", "sequence", "link_state", "destination", "next_hop",
                     "position", "message", "timestamp", "hop_count"])
application_layer_address = "tcp://127.0.0.1:5557"  # application layer address
network_layer_up_stream_address = "tcp://127.0.0.1:5555"  # network layer up stream

name_self = ""

time_file = None

network_layer_queue = queue.Queue()


def get_message_to_send():
    # get a message from user and send it
    # commit
    while True:
        command = input("command (auto or manual): ")
        if command == "auto":
            get_messages_from_file()
        else:
            message = input("message: ")
            destination = input("destination: ")

            packet_to_send = packet("DATA", "", "", "", {}, destination, "", "", message, time.time(), 0)
            network_layer_queue.put(pickle.dumps(packet_to_send))


def get_messages_from_file():
    input_file = open("input_" + name_self + ".txt", "r")
    commands = input_file.read().splitlines()
    for command in commands:
        message, destination = command.split(" ")
        packet_to_send = packet("DATA", "", "", "", {}, destination, "", "", message, time.time(), 0)
        print("packet: ", packet_to_send)
        network_layer_queue.put(pickle.dumps(packet_to_send))
        time.sleep(0.1)
    input_file.close()
    print("\nfinished sending messages from file")


def signal_handler(signal, frame):
    context.term()
    context.destroy()
    time_file.close()
    sys.exit()


def read_config_file(filename, name):
    global application_layer_address, network_layer_up_stream_address, name_self, time_file
    config = configparser.ConfigParser()
    config.read(filename)
    name_self = name
    time_file = open("time" + name + ".txt", "w+")

    node_settings = config[name]
    application_layer_address = node_settings["application_layer_address"]
    network_layer_up_stream_address = node_settings["network_layer_up_stream_address"]


def network_layer_informer():
    client_socket = context.socket(zmq.PUSH)
    client_socket.connect(network_layer_up_stream_address)
    while True:
        message_raw = network_layer_queue.get()
        client_socket.send(message_raw)


def network_layer_listener():
    server_socket = context.socket(zmq.PULL)
    server_socket.bind(application_layer_address)
    server_socket.setsockopt(zmq.LINGER, 0)

    while True:
        received_message = server_socket.recv()
        # process received message here
        message = pickle.loads(received_message)
        # todo here we need to check the type of the message.
        if message.type in ["neighbor", "election", "ack", "leader"]:
            print(message)
        elapsed_time = time.time() - message.timestamp
        print("\n (Application Layer) message \"%s\" received from %s within %f seconds in %d hops" %
              (message.message, message.name, elapsed_time, message.hop_count + 1), flush=True)
        time_file.write("%s %d %f\r\n" % (message.name, message.hop_count + 1, elapsed_time))
        # break on some condition


if __name__ == "__main__":
    context = zmq.Context()
    signal.signal(signal.SIGINT, signal_handler)

    read_config_file("config.ini", sys.argv[1])

    prompt_thread = threading.Thread(target=get_message_to_send, args=())
    network_layer_informer_thread = threading.Thread(target=network_layer_informer, args=())
    network_layer_listener_thread = threading.Thread(target=network_layer_listener, args=())

    prompt_thread.start()
    network_layer_informer_thread.start()
    network_layer_listener_thread.start()

    prompt_thread.join()
    network_layer_informer_thread.join()
    network_layer_listener_thread.join()
