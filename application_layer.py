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

election_queue = queue.Queue()

neighbor_list = []

topology_table = {}

neighbor_list_acknowledges = {}

parent_node = None

candidate_leader = None


def start_election(name):
    election_queue.put("start " + name)


def elect():
    message = election_queue.get()
    if message == "start bully":
        bully("", True)
    elif message == "start aefa":
        aefa("", True)

    elif message.elec_type == "BULLY":
        bully(message, False)
    elif message.elec_type == "AEFA":
        aefa(message, False)


def bully(first_message, start):
    if start:
        pass  # send first election message
    else:
        bully_process_message(first_message)
    while True:
        election_message = election_queue.get()
        bully_process_message(election_message)


def bully_process_message(message):
    pass


def aefa(first_message, start):
    if start:
        for neighbor in neighbor_list:
            message = aefa_generate_message("ELECTION", neighbor)
            neighbor_list_acknowledges[neighbor] = False
            network_layer_queue.put(pickle.dumps(message))
        pass  # send first election message
    else:
        aefa_process_message(first_message)
    while True:
        election_message = election_queue.get()
        aefa_process_message(election_message)


def aefa_process_message(message):
    global parent_node, candidate_leader
    # todo: if received an election packet, send it to the neighbors but not to the parent
    # todo: until all the neighbors returned ACK message back, wait.
    # todo: if there is no neighbor to send the packet except the parent, then return ACK message
    # todo: when all neighbors/children sent back ACK message to the parent, return ACK message
    # todo: if parent is null, then it means it is the one that initiated the ELECTION.
    # todo: once initiator received ACK messages, inform all the nodes about LEADER
    message_type = message.type
    if message_type == "ELECTION":
        # todo: can we support asynchronous election?
        # todo: what if we continue with the election that has been started by the min/max identifier.
        parent_node = message.source
        # check for the neighbors.
        message_sent = False
        for neighbor in neighbor_list:
            if neighbor != parent_node:
                message_sent = True
                message_to_send = aefa_generate_message("ELECTION", neighbor)
                network_layer_queue.put(pickle.dumps(message_to_send))
        if message_sent:
            return
        else:
            # no neighbor to inform about election.
            # todo: return ACK message back to parent. if no parent exist, you are the only one in the network.
            # todo: declare yourself as leader.
            if parent_node:
                message_to_send = aefa_generate_message("ACK", parent_node)
                network_layer_queue.put(pickle.dumps(message_to_send))
    elif message_type == "ACK":
        # todo: check whether all neighbors returned ACK or not.
        # todo: if so, return ACK to the parent.
        # todo: if there is no parent, then declare the leader.
        neighbor_list_acknowledges[message.source] = True
        received_all_acks = True
        candidate_leader = message.source if message.source > candidate_leader else candidate_leader
        for neighbor in neighbor_list_acknowledges:
            received_all_acks = received_all_acks and neighbor_list_acknowledges[neighbor]

        if received_all_acks:
            if parent_node:
                message_to_send = aefa_generate_message("ACK", parent_node, candidate_leader)
                network_layer_queue.put(pickle.dumps(message_to_send))
            else:
                # todo: you are the one that initiated the connection. Broadcast the LEADER messages.
                for node in topology_table:
                    message_to_send = aefa_generate_message("LEADER", node, candidate_leader)
                    network_layer_queue.put(pickle.dumps(message_to_send))
    elif message_type == "LEADER":
        # todo: leader message is received. now you can measure the time.
        # todo: terminate if you want to. this is the end of the algorithm.
        # todo: flood leader packets just like ack packages.
        print("leader is : {}".format(message.message))
    pass


def aefa_generate_message(message_type, destination, message_info=""):
    message = packet(["AEFA", message_type], "", "", "", {}, destination, "", "", message_info, time.time(), 0)
    return message


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
    global neighbor_list, topology_table, candidate_leader
    candidate_leader = name_self

    server_socket = context.socket(zmq.PULL)
    server_socket.bind(application_layer_address)
    server_socket.setsockopt(zmq.LINGER, 0)

    while True:
        received_message = server_socket.recv()
        # process received message here
        message = pickle.loads(received_message)
        # todo here we need to check the type of the message.
        if message.type != "DATA":
            if message.type == "neighbor":
                neighbor_list = message.link_state[name_self]
            elif message.type == "topology":
                topology_table = message.link_state[name_self]
            else:
                election_queue.put(message)
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
