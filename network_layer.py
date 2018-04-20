import zmq
import threading
import queue  # I am not sure if we need a queue or not.
import pickle
import sys
import configparser

from collections import namedtuple

packet = namedtuple("packet", ["type", "source", "destination", "next_hop", "position", "message"])

routing_table_mutex = threading.Lock()
# this is a dictionary that we can keep names to corresponding IPs, also necessary routing information.

routing_table = {}

link_layer_message_queue = queue.Queue()  # queue holds messages in original format.

link_layer_address = "tcp://127.0.0.1:5554"  # link layer address

network_layer_up_stream_address = "tcp://127.0.0.1:5555"  # network layer up stream

network_layer_down_stream_address = "tcp://127.0.0.1:5556"  # network layer down stream

app_layer_address = "tcp://127.0.0.1:5557"  # application layer

ip_address_self = ""


# here define rooting algorithm

# here we need atomic data structure for rooting algorithm


def periodic_update_location():
    pass


def find_routing(destination):
    # check routing table to find the next hop.
    routing_table_mutex.acquire()
    try:
        next_hop = routing_table[destination]
    except KeyError:
        next_hop = "something"
    routing_table_mutex.release()
    return next_hop


def query_address():
    pass


def update_routing_table(message):
    # here we need to to update routing table based on the algorithm we use.
    routing_table_mutex.acquire()
    pass
    routing_table_mutex.relase()


def _is_control_message(message_type):
    return message_type == "broad" or message_type == "update"


def _is_destination_self(destination):
    return destination == ip_address_self


def link_layer_listener():
    server_socket = context.socket(zmq.REP)
    server_socket.bind(network_layer_down_stream_address)
    server_socket.setsockopt(zmq.LINGER, 0)

    client_socket = context.socket(zmq.REQ)
    client_socket.connect(app_layer_address)

    while True:
        message_raw = server_socket.recv()
        message = pickle.loads(message_raw)

        if _is_control_message(message.type):
            update_routing_table(message)
        elif _is_destination_self(message.destination):
            client_socket.send(message_raw)
        else:
            link_layer_message_queue.put(message)


def app_layer_listener():
    # if the message contains control type flag, we should update the routing table we have.
    server_socket = context.socket(zmq.REP)
    server_socket.bind(network_layer_up_stream_address)
    server_socket.setsockopt(zmq.LINGER, 0)

    while True:
        message = server_socket.recv()
        link_layer_message_queue.put(pickle.loads(message))


def link_layer_client():
    client_socket = context.socket(zmq.REQ)
    client_socket.connect(link_layer_address)
    while True:
        message = link_layer_message_queue.get()

        message._replace(next_hop=find_routing(message.destination))

        client_socket.send(pickle.dumps(message))

    pass


def read_config_file(filename, name):
    global ip_address_self

    config = configparser.ConfigParser()
    config.read(filename)
    default_settings = config["DEFAULT"]
    node_settings = config[name]
    ip_address_self = node_settings["ip"]
    port_read = ip_address_self.split(":")
    ip_address_self = (port_read[0], int(port_read[1][:-1]))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Arguments are not valid. Usage: [name of the node]")
        exit(-1)

    read_config_file("config.ini", sys.argv[1])
    context = zmq.Context()

    network_layer_up_thread = threading.Thread(target=app_layer_listener, args=())
    network_layer_down_thread = threading.Thread(target=link_layer_listener, args=())
    link_layer_client_thread = threading.Thread(target=link_layer_client, args=())

    network_layer_up_thread.start()
    network_layer_down_thread.start()
    link_layer_client_thread.start()

    network_layer_down_thread.join()
    network_layer_up_thread.join()
    link_layer_client_thread.join()
