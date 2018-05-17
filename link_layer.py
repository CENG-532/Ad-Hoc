import zmq
import time
import sys
import socket
import threading
import pickle
import queue
import configparser
import signal

from math import sqrt, pow
from collections import namedtuple

# have MAC layout to match ip to mac or use IP right away.

server_message_queue = queue.Queue()  # queue holds raw values of messages in byte format.

position_self = (3, 4)  # some position

communication_range = 10

node_id = 10

packet = namedtuple("packet",
                    ["type", "source", "name", "sequence", "link_state", "destination", "next_hop",
                     "position", "message", "timestamp", "hop_count"])

network_layer_down_stream_address = "tcp://127.0.0.1:5556"  # network layer down stream

link_layer_up_stream_address = "tcp://127.0.0.1:5554"  # link layer up stream

ip_address_self = "127.0.0.1"

link_layer_broadcast_port_number = None
link_layer_data_port_number = None

name_self = None
broadcast_address = None
close_tcp_connections = False

ip_address_to_tcp_queue = {}


def get_ip(message):
    # we need both port numbers and IP addresses of destination.
    # return message.next_hop
    # test:
    return message.next_hop if message.next_hop != "" else message.destination


def update_mac_table(message):
    # here we might want to update mac table if we decide to use different convention than IP addressing.
    pass


def calculate_distance(position):
    return sqrt(pow(position[0] - position_self[0], 2) + pow(position[1] - position_self[1], 2))


def is_in_range(position):
    # here we need to set our distance to something, and compare it with the received message.
    # omit the message if it is not in our range.
    return calculate_distance(position) <= communication_range


def worker_network_layer_informer(context):
    print("worker thread is started.")
    client_socket = context.socket(zmq.PUSH)
    client_socket.connect(network_layer_down_stream_address)

    while True:
        message_raw = server_message_queue.get()
        message = pickle.loads(message_raw)

        if is_in_range(message.position) and message.name != name_self:
            # print("message is loaded:", message)
            client_socket.send(message_raw)


def network_layer_listener():
    # print("network layer listener is started")
    server_socket = context.socket(zmq.PULL)
    server_socket.bind(link_layer_up_stream_address)
    server_socket.setsockopt(zmq.LINGER, 0)

    udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    active_connections = []

    while True:
        message_raw = server_socket.recv()
        message = pickle.loads(message_raw)
        # depending on the message command, which can be decided after a discussion, we can define set of commands.
        ip = get_ip(message)
        if ip == -1:
            continue
        if ip[0] != broadcast_address:
            # here put the datagram to the queue of tcp connection
            print("this message is being sent", message)
            try:
                ip_address_to_tcp_queue[ip[0]].put(message_raw)
            except KeyError:
                # todo: you need to connect to the destination.
                try:
                    tcp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    print("connecting to the ip:{} [{}]".format(ip[0], link_layer_data_port_number))
                    tcp_client_socket.connect((ip[0], link_layer_data_port_number))
                    active_connections.append(threading.Thread(target=worker_data_sender,
                                                               args=(tcp_client_socket, ip[0],)))
                    ip_address_to_tcp_queue[ip[0]] = queue.Queue()
                    ip_address_to_tcp_queue[ip[0]].put(message_raw)
                    active_connections[-1].start()
                    active_connections.append(threading.Thread(target=worker_data_receiver,
                                                               args=(tcp_client_socket, ip[0],)))
                    active_connections[-1].start()
                except OSError:
                    print("got OSerror")
                    continue

        # since we only care about ip address of the message to be sent, there is no need to check for extra stuff here.
        # print(message)
        else:
            udp_client.sendto(message_raw, ip)

    for worker in active_connections:
        worker.join()


# data - broadcast
# data thread, every connection is thread (select)
# every ip_address -> tcp_thread = data queue


def link_layer_broadcast_listener():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", link_layer_broadcast_port_number))

    worker_thread = threading.Thread(target=worker_network_layer_informer, args=(context,))
    worker_thread.start()

    while True:
        message = server_socket.recv(10240)

        message_decoded = pickle.loads(message)
        if message_decoded.type == "DATA":
            print("BROADCAST listener GOT this: ", message_decoded)
            continue
        server_message_queue.put(message)


    worker_thread.join()


def worker_data_sender(client_socket, addr):
    # something is wrong here. What has to be done is that there has to be an another thread that
    # listens the client socket at the other end.
    local_terminate_flag = False
    while True:
        message_raw = ip_address_to_tcp_queue[addr].get()
        print("sending data over tcp", pickle.loads(message_raw))
        try:
            client_socket.send(message_raw)
        except ConnectionError:
            local_terminate_flag = True

        if close_tcp_connections or local_terminate_flag:
            client_socket.close()
            del ip_address_to_tcp_queue[addr]
            break


def worker_data_receiver(client_socket, addr):
    local_terminate_flag = False
    while True:
        try:
            message_raw = client_socket.recv(1024)
            server_message_queue.put(message_raw)
        except ConnectionError:
            local_terminate_flag = True

        if close_tcp_connections or local_terminate_flag:
            client_socket.close()
            del ip_address_to_tcp_queue[addr]
            break


def link_layer_data_listener():
    # this will listen tcp
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", link_layer_data_port_number))
    server_socket.listen(10)
    active_connection_list = []
    while True:
        connection_socket, addr = server_socket.accept()
        ip_address_to_tcp_queue[addr[0]] = queue.Queue()
        active_connection_list.append(threading.Thread(target=worker_data_sender, args=(connection_socket, addr[0],)))
        active_connection_list[-1].start()
        active_connection_list.append(threading.Thread(target=worker_data_receiver, args=(connection_socket, addr[0],)))
        active_connection_list[-1].start()

    for connection in active_connection_list:
        connection.join()


def read_config_file(filename, name):
    global ip_address_self, communication_range, position_self, link_layer_broadcast_port_number, name_self
    global network_layer_down_stream_address, link_layer_up_stream_address, link_layer_data_port_number
    global broadcast_address

    config = configparser.ConfigParser()
    config.read(filename)

    default_settings = config["DEFAULT"]
    node_settings = config[name]
    name_self = name

    network_layer_down_stream_address = node_settings["network_layer_down_stream_address"]
    link_layer_up_stream_address = node_settings["link_layer_up_stream_address"]

    ip_address_self = node_settings["ip"]
    link_layer_broadcast_port_number = int(default_settings["link_layer_broadcast_port_number"])
    link_layer_data_port_number = int(default_settings["link_layer_data_port_number"])
    broadcast_address = default_settings["broadcast_address"]

    ip_address_self = (ip_address_self, link_layer_broadcast_port_number)

    print(ip_address_self, flush=True)

    position_self = (float(node_settings["positionX"]), float(node_settings["positionX"]))
    communication_range = float(config["DEFAULT"]["range"])


def signal_handler(signal, frame):
    context.term()
    context.destroy()
    sys.exit()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Arguments are not valid. Usage: [name of the node]", flush=True)
        exit(-1)

    context = zmq.Context()

    signal.signal(signal.SIGINT, signal_handler)

    read_config_file("config.ini", sys.argv[1])

    link_layer_data_listener_thread = threading.Thread(target=link_layer_data_listener, args=())
    link_layer_server_thread = threading.Thread(target=link_layer_broadcast_listener, args=())
    network_layer_listener_thread = threading.Thread(target=network_layer_listener, args=())

    link_layer_server_thread.start()
    network_layer_listener_thread.start()
    link_layer_data_listener_thread.start()

    link_layer_server_thread.join()
    network_layer_listener_thread.join()
    link_layer_data_listener_thread.join()

