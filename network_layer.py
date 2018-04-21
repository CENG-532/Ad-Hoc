import zmq
import threading
import queue  # I am not sure if we need a queue or not.
import pickle
import sys
import configparser
import math
import time

from collections import namedtuple

packet = namedtuple("packet",
                    ["type", "source", "name", "sequence", "link state", "destinationName", "destinationIP", "next_hop", "position",
                     "message"])

routing_table_mutex = threading.Lock()
# this is a dictionary that we can keep names to corresponding IPs, also necessary routing information.

neighbor_list = []  # nodes that are adjacent to the current node. (name, pos)

topology_table = {"link state": {}, "sequence": {}}  # will consist of link state information of node j and the sequence

next_hop_table = {}

distance_table = {}

sequence = 0

clock_interval_by_hops = []

fish_eye_ranges = []

number_of_scope = 2

known_nodes = []

link_layer_message_queue = queue.Queue()  # queue holds messages in original format.

link_layer_address = "tcp://127.0.0.1:5554"  # link layer address

network_layer_up_stream_address = "tcp://127.0.0.1:5555"  # network layer up stream

network_layer_down_stream_address = "tcp://127.0.0.1:5556"  # network layer down stream

app_layer_address = "tcp://127.0.0.1:5557"  # application layer

ip_address_self = ""

port_number_self = None

name_self = ""

position_self = None

link_layer_port_number = None


# here define rooting algorithm

# here we need atomic data structure for rooting algorithm

def node_init():
    # the initialization message that all nodes are going to send to each other.
    message = packet("Pbroad", ip_address_self, name_self, sequence, "", ("255.255.255.255", link_layer_port_number),
                     "", position_self, "")
    link_layer_message_queue.put(message)


def calculate_distance(pos1, pos2):
    return math.sqrt(math.pow(pos1[0] - pos2[0], 2) + math.pow(pos1[1] - pos2[1], 2))


def find_shortest_path():
    global position_self
    # dijkstra shortest-path algorithm
    p = [name_self]
    distance_table[name_self] = 0
    for x, pos_x in known_nodes:
        if x is not name_self:
            if x in topology_table["link state"][name_self]:
                distance_table[x] = calculate_distance(position_self, pos_x)
                next_hop_table[x] = x  # paper says k instead of x
            else:
                distance_table[x] = math.inf
                next_hop_table[x] = -1  # paper says k instead of x

    while list(set(known_nodes) - set(p)):
        min_k, min_l, min_pos_k, min_pos_l = "", "", 0, 0  # most probably redundant
        min_distance = math.inf
        for k, pos_k in list(set(known_nodes) - set(p)):
            for l, pos_l in p:
                distance = calculate_distance(pos_l, pos_k) + distance_table[l]
                if distance < min_distance:
                    min_distance = distance
                    min_k, min_pos_k, min_l, min_pos_l = k, pos_k, l, pos_l
        if min_k:  # most probably redundant
            p.append((min_k, min_pos_k))
            distance_table[min_k] = distance_table[min_l] + min_distance
            next_hop_table[min_k] = next_hop_table[min_l]


def process_packet(message):
    source = message.source
    name = message.name
    packet_sequence = int(message.sequence)
    packet_link_state = message.link_state
    try:
        topology_table["link state"][name] = topology_table["link state"][name] + source
    except KeyError:
        topology_table["link state"][name] = [source]  # currently under development

    for node_name in known_nodes:
        if node_name != name_self and packet_sequence > topology_table["sequence"][node_name]:
            topology_table["sequence"][node_name] = packet_sequence
            topology_table["link state"][node_name] = packet_link_state


def check_neighbors():
    to_be_deleted_neighbors = []
    for neighbor in neighbor_list:
        try:
            if distance_table[neighbor] == sys.maxsize:
                to_be_deleted_neighbors.append(neighbor)
        except KeyError:
            continue

    for neighbor in to_be_deleted_neighbors:
        neighbor_list.remove(neighbor)


def periodic_routing_update():
    global sequence
    sequence += 1

    # I have added necessary parts roughly. We can check both the packet type and structural design tomorrow.

    topology_table["link state"][name_self] = []
    topology_table["sequence"][name_self] = sequence

    message = packet("Pupdate", ip_address_self, name_self, sequence, "link state here", "255.255.255.255", "",
                     position_self, "")

    for node in neighbor_list:
        topology_table["link state"][name_self].append(node)

    for node, _ in known_nodes:
        for scope in range(number_of_scope):
            clock = clock_interval_by_hops[scope]
            fish_eye_range = fish_eye_ranges[scope]
            if distance_table[node] < fish_eye_range and clock % 1000:
                message._replace(topology_table=message.topology_table + topology_table["link state"][node])


def find_routing(destination):
    # check routing table to find the next hop.
    routing_table_mutex.acquire()
    try:
        next_hop = next_hop_table[destination]
    except KeyError:
        next_hop = ""
    routing_table_mutex.release()
    return next_hop


def query_address():
    pass


def update_routing_table(message):
    # here we need to to update routing table based on the algorithm we use.
    routing_table_mutex.acquire()
    pass
    routing_table_mutex.release()

    process_packet(message)
    # here reset the topology table I guess,
    # we need to check the structure here as well.
    topology_table["link state"][name_self] = neighbor_list
    find_shortest_path()
    periodic_routing_update()


def _is_control_message(message_type):
    return message_type == "broad" or message_type == "update"


def _is_destination_self(destination):
    return destination == ip_address_self


def link_layer_listener():
    server_socket = context.socket(zmq.PULL)
    server_socket.bind(network_layer_down_stream_address)
    server_socket.setsockopt(zmq.LINGER, 0)

    client_socket = context.socket(zmq.PUSH)
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
    server_socket = context.socket(zmq.PULL)
    server_socket.bind(network_layer_up_stream_address)
    server_socket.setsockopt(zmq.LINGER, 0)

    node_init()

    while True:
        message = server_socket.recv()
        link_layer_message_queue.put(pickle.loads(message))


def link_layer_client():
    client_socket = context.socket(zmq.PUSH)
    client_socket.connect(link_layer_address)
    while True:
        message = link_layer_message_queue.get()

        next_hop = find_routing(message.destination)

        message._replace(next_hop=find_routing(message.destination))

        client_socket.send(pickle.dumps(message))

    pass


def read_config_file(filename, name):
    global ip_address_self, name_self, position_self, clock_interval_by_hops
    global number_of_scope, port_number_self, link_layer_port_number

    name_self = name
    config = configparser.ConfigParser()
    config.read(filename)
    default_settings = config["DEFAULT"]
    node_settings = config[name]
    ip_address_self = node_settings["ip"]
    port_read = ip_address_self.split(":")
    port_number_self = int(port_read[1][:-1])
    ip_address_self = (port_read[0], port_number_self)
    link_layer_port_number = default_settings["link_layer_port_number"]

    clock_interval_by_hops.append(int(default_settings["clock_interval_hop_1"]))
    clock_interval_by_hops.append(int(default_settings["clock_interval_hop_2"]))

    fish_eye_ranges.append(int(default_settings["fish_eye_range_1"]))
    fish_eye_ranges.append(int(default_settings["fish_eye_range_2"]))

    number_of_scope = len(fish_eye_ranges)

    position_self = (float(node_settings["positionX"]), float(node_settings["positionX"]))


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
