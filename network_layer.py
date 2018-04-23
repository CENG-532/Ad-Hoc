import zmq
import threading
import queue  # I am not sure if we need a queue or not.
import pickle
import sys
import configparser
import math
import time
import signal

from collections import namedtuple

packet = namedtuple("packet",
                    ["type", "source", "name", "sequence", "link_state", "destination", "next_hop",
                     "position",
                     "message"])

routing_table_mutex = threading.RLock()

topology_table_mutex = threading.RLock()
# this is a dictionary that we can keep names to corresponding IPs, also necessary routing information.

neighbor_list = []  # nodes that are adjacent to the current node. (name, pos)

topology_table = {}
# topology_table = {"name": {"address":, "sequence":, "lastHeardTime":, "neighbor_list":, "needToSend:" bool}}

routing_table = {}

sequence = 0

scope_interval = []

scope_clocks = []

fish_eye_scopes = []

number_of_scopes = 2

known_nodes = {}

link_layer_message_queue = queue.Queue()  # queue holds messages in original format.

link_layer_address = "tcp://127.0.0.1:5554"  # link layer address

network_layer_up_stream_address = "tcp://127.0.0.1:5555"  # network layer up stream

network_layer_down_stream_address = "tcp://127.0.0.1:5556"  # network layer down stream

app_layer_address = "tcp://127.0.0.1:5557"  # application layer

ip_address_self = (None, None)

port_number_self = None

name_self = ""

position_self = None

link_layer_port_number = None

topology_table_changed = False

max_last_heard_time = None

broad_cast_address = None


# here define rooting algorithm

# here we need atomic data structure for rooting algorithm

def node_init():
    global topology_table
    # the initialization message that all nodes are going to send to each other.
    topology_table[name_self] = {}
    topology_table[name_self]["ip_address"] = ip_address_self
    topology_table[name_self]["neighbor_list"] = []
    topology_table[name_self]["position"] = position_self
    topology_table[name_self]["need_to_send"] = False
    topology_table[name_self]["sequence_number"] = 0
    topology_table[name_self]["last_heard_time"] = time.time()

    message = packet("broadcast", ip_address_self, name_self, sequence, topology_table,
                     broad_cast_address,
                     "", position_self, "")
    link_layer_message_queue.put(message)


def calculate_distance(pos1, pos2):
    return math.sqrt(math.pow(pos1[0] - pos2[0], 2) + math.pow(pos1[1] - pos2[1], 2))


def find_shortest_path():
    global position_self
    global routing_table
    global topology_table_changed

    # dijkstra shortest-path algorithm
    routing_table[name_self] = {"dest_addr": ip_address_self, "next_hop": ip_address_self, "distance": 0}
    p = [(name_self, position_self)]
    topology_table_mutex.acquire()

    for x in known_nodes:
        pos_x = topology_table[x]["position"]
        if x is not name_self:
            routing_table[x] = {}
            if x in topology_table[name_self]["neighbor_list"]:
                routing_table[x]["distance"] = calculate_distance(position_self, pos_x)
                routing_table[x]["next_hop"] = topology_table[x]["ip_address"]
            else:
                routing_table[x]["distance"] = math.inf
                routing_table[x]["next_hop"] = -1

    is_changed = False
    while list(set(known_nodes) - set(p)):
        min_k, min_l, min_pos_k, min_pos_l = "", "", 0, 0
        for k in topology_table:
            if k == name_self:
                continue
            pos_k = topology_table[k]["position"]
            min_distance = routing_table[k]["distance"]
            for l in list(set(known_nodes) - set(p)):
                pos_l = topology_table[l]["position"]
                distance = calculate_distance(pos_l, pos_k) + routing_table[l]["distance"]
                if round(distance, 2) < round(min_distance, 2):
                    is_changed = True
                    min_distance = distance
                    min_k, min_pos_k, min_l, min_pos_l = k, pos_k, l, pos_l
            p.append(k)
            if is_changed:
                is_changed = False
                routing_table[min_k]["distance"] = min_distance
                routing_table[min_k]["next_hop"] = routing_table[min_l]["next_hop"]

    topology_table_changed = False

    topology_table_mutex.release()


def process_packet(message):
    # process packet cannot get the lock, which is because periodic update runs more.
    global topology_table, topology_table_changed
    global sequence, known_nodes

    topology_table_changed = False

    source = message.source
    name = message.name

    position = message.position
    packet_sequence = int(message.sequence)
    packet_link_state = message.link_state

    topology_table_mutex.acquire()
    known_nodes[name] = 1

    if name in topology_table[name_self]["neighbor_list"]:
        topology_table[name]["position"] = position
        topology_table[name]["sequence_number"] += 1
        topology_table_changed = True
    else:
        topology_table[name_self]["neighbor_list"].append(name)
        # print("packet_link_stat: ", packet_link_state)
        topology_table_changed = True

    print("topo in process: ", topology_table)

    for dest_in_packet in packet_link_state:
        if dest_in_packet not in topology_table:
            topology_table[dest_in_packet] = packet_link_state[dest_in_packet]
            topology_table[dest_in_packet]["sequence_number"] += 1
            topology_table[dest_in_packet]["last_heard_time"] = time.time()
            topology_table_changed = True
        else:
            if topology_table[dest_in_packet]["sequence_number"] < packet_link_state[dest_in_packet]["sequence_number"]:
                topology_table[dest_in_packet] = packet_link_state[dest_in_packet]
                topology_table[dest_in_packet]["last_heard_time"] = time.time()
                topology_table_changed = True
            else:
                topology_table[name]["need_to_send"] = True

    topology_table_mutex.release()


def check_neighbors():
    to_be_deleted_neighbors = []
    for neighbor in topology_table[name_self]["neighbor_list"]:
        try:
            if routing_table[neighbor]["distance"] == sys.maxsize:
                to_be_deleted_neighbors.append(neighbor)
        except KeyError:
            continue

    for neighbor in to_be_deleted_neighbors:
        topology_table[name_self]["neighbor_list"].remove(neighbor)


def clear_neighbors(to_be_deleted_neighbors):
    for neighbor in to_be_deleted_neighbors:
        topology_table[name_self]["neighbor_list"].remove(neighbor)


def check_elapsed_time(current_time, scope):
    is_changed = (current_time - scope_clocks[scope]) * 1000 > scope_interval[scope]
    if is_changed:
        scope_clocks[scope] = time.time()
    return is_changed


def periodic_routing_update():
    global sequence, max_last_heard_time, number_of_scopes

    # I have added necessary parts roughly. We can check both the packet type and structural design tomorrow.
    while True:
        to_be_deleted_neighbors = []

        current_time = time.time()

        # for neighbor in topology_table[name_self]["neighbor_list"]:
        #     if topology_table[neighbor]["last_heard_time"] + max_last_heard_time < current_time:
        #         to_be_deleted_neighbors.append(neighbor)
        #

        clear_neighbors(to_be_deleted_neighbors)

        message = packet("broadcast", ip_address_self, name_self, sequence, {name_self: topology_table[name_self]},
                         broad_cast_address, "", position_self, "")

        link_state_changed = False

        inserted_nodes = []
        print("topo in period:", topology_table)

        for scope in range(number_of_scopes):
            fish_eye_range = fish_eye_scopes[scope]
            is_time_elapsed = check_elapsed_time(current_time, scope)
            for node in known_nodes:
                routing_table_mutex.acquire()
                topology_table_mutex.acquire()
                try:
                    if node not in inserted_nodes and routing_table[node]["distance"] < fish_eye_range and is_time_elapsed:
                        message.link_state[node] = topology_table[node]
                        inserted_nodes.append(node)
                        link_state_changed = True
                except KeyError:
                    pass
                topology_table_mutex.release()
                routing_table_mutex.release()

        # print("ben icindeyim, al bu da flaG:", link_state_changed)

        if link_state_changed:
            sequence += 1
            link_layer_message_queue.put(message)


def find_routing(destination):
    # check routing table to find the next hop.
    routing_table_mutex.acquire()
    try:
        next_hop = routing_table[destination]["next_hop"]
    except KeyError:
        next_hop = ""
    routing_table_mutex.release()
    return next_hop


def query_address():
    pass


def update_routing_table(message):
    # here we need to to update routing table based on the algorithm we use.
    routing_table_mutex.acquire()
    process_packet(message)

    if topology_table_changed:
        find_shortest_path()

    routing_table_mutex.release()

    # here reset the topology table I guess,
    # we need to check the structure here as well.


def _is_control_message(message_type):
    return message_type == "broadcast" or message_type == "update"


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

        if not _is_control_message(message.type):
            message = message._replace(next_hop=find_routing(message.destination))

        client_socket.send(pickle.dumps(message))


def read_config_file(filename, name):
    global ip_address_self, name_self, position_self, scope_interval
    global number_of_scopes, port_number_self, link_layer_port_number
    global max_last_heard_time
    global scope_clocks, broad_cast_address

    name_self = name
    config = configparser.ConfigParser()
    config.read(filename)
    default_settings = config["DEFAULT"]
    node_settings = config[name]

    ip_address_self = node_settings["ip"]
    link_layer_port_number = int(default_settings["link_layer_port_number"])

    ip_address_self = (ip_address_self, link_layer_port_number)
    broad_cast_address = ("127.255.255.255", link_layer_port_number)

    print(ip_address_self)

    scope_interval.append(int(default_settings["scope_interval_1"]))
    scope_interval.append(int(default_settings["scope_interval_2"]))

    fish_eye_scopes.append(int(default_settings["fish_eye_scope_1"]))
    fish_eye_scopes.append(int(default_settings["fish_eye_scope_2"]))

    max_last_heard_time = int(default_settings["max_last_heard_time"])

    number_of_scopes = len(fish_eye_scopes)

    position_self = (float(node_settings["positionX"]), float(node_settings["positionX"]))

    current_time = time.time()

    scope_clocks = [current_time for _ in scope_interval]


def signal_handler(signal, frame):
    context.term()
    context.destroy()
    sys.exit()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Arguments are not valid. Usage: [name of the node]")
        exit(-1)

    read_config_file("config.ini", sys.argv[1])
    context = zmq.Context()

    signal.signal(signal.SIGINT, signal_handler)

    network_layer_up_thread = threading.Thread(target=app_layer_listener, args=())
    network_layer_down_thread = threading.Thread(target=link_layer_listener, args=())
    link_layer_client_thread = threading.Thread(target=link_layer_client, args=())
    periodic_update_thread = threading.Thread(target=periodic_routing_update, args=())

    network_layer_up_thread.start()
    network_layer_down_thread.start()
    link_layer_client_thread.start()
    periodic_update_thread.start()

    network_layer_down_thread.join()
    network_layer_up_thread.join()
    link_layer_client_thread.join()
    periodic_update_thread.join()
