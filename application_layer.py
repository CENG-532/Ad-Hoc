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

bully_wait_time = 3

bully_dict = {"ack": {"sent": [], "received": []},
              "elect": {"sent": [], "received": []},
              "grant": {"sent": [], "received": []},
              "victory": {"sent": [], "received": []}}

elect_start_time = 0

neighbor_list_acknowledges = {}

parent_node = None

candidate_leader = None

election_finished = False


def start_election(name):
    election_queue.put("start " + name)


def elect():
    global elect_start_time
    bully_reset()
    aefa_reset()
    message = election_queue.get()
    print("election function message: ", message)
    try:
        print("election type : ", message.type[0], message.type[1])
    except Exception:
        pass
    elect_start_time = time.time()
    if message == "start bully":
        bully("", True)
    elif message == "start aefa":
        aefa("", True)

    elif message.type[0] == "BULLY":
        bully(message, False)
    elif message.type[0] == "AEFA":
        print("message_Type: ", message.type)
        aefa(message, False)


def bully(first_message, start):
    if start:
        bully_start()
    else:
        bully_process_message(first_message)
    while True:
        election_message = election_queue.get()
        bully_process_message(election_message)


def bully_start():
    for node_name in topology_table:
        if node_name > name_self:
            # print("send elect message to {}".format(node_name))
            bully_send("elect", node_name)


def bully_send(message_type, destination):
    packet_to_send = packet(["BULLY", message_type.upper()], "", "", "", {}, destination, "", "", "", time.time(),
                            0)
    bully_dict[message_type]["sent"].append(destination)
    network_layer_queue.put(pickle.dumps(packet_to_send))


def bully_process_message(message):
    message_source = message.name
    if message.type[1] == "ELECT":
        # print("got elect message from {}".format(message_source))
        # if bully_dict["elect"]["received"]:
        #     if min(bully_dict["elect"]["received"]) < message_source:
        #         print("previous elect is smaller than this. Ignoring...")
        #         return
        bully_dict["elect"]["received"].append(message_source)
        bully_send("ack", message_source)
    elif message.type[1] == "ACK":
        # print("got ack message from {}".format(message_source))
        bully_dict["ack"]["received"].append(message_source)
        if len(bully_dict["ack"]["received"]) == len(bully_dict["elect"]["sent"]):
            winner = max(bully_dict["ack"]["received"])
            # print("send grant message to {}".format(winner))
            # if bully_dict["elect"]["received"]:
            #     if min(bully_dict["elect"]["received"]) < message_source:
            #         print("previous elect is smaller than this. Ignoring grant...")
            #         return

            bully_send("grant", winner)
        else:
            pass  # TODO add a timer to check ack timeout

    elif message.type[1] == "GRANT":
        print("\n\nThis node is selected LEADER\n\n")
        for node_name in topology_table:
            if node_name != name_self:
                print("send victory message to {}".format(node_name))
                bully_send("victory", node_name)
        elect()
    elif message.type[1] == "VICTORY":
        print("\nleader is selected in {}\n".format(time.time() - elect_start_time))
        print("\n{} is the leader\n".format(message_source))
        elect()
    else:
        print("something wrong with bully message:")
        print(message)


def bully_reset():
    global bully_dict
    bully_dict = {"ack": {"sent": [], "received": []},
                  "elect": {"sent": [], "received": []},
                  "grant": {"sent": [], "received": []},
                  "victory": {"sent": [], "received": []}}


def aefa_reset():
    pass  # TODO reset all variables


def aefa(first_message, start):
    global parent_node
    if start:
        for neighbor in neighbor_list:
            message = aefa_generate_message("ELECTION", neighbor)
            neighbor_list_acknowledges[neighbor] = False
            network_layer_queue.put(pickle.dumps(message))
            parent_node = name_self
    else:
        aefa_process_message(first_message)

    while True:
        election_message = election_queue.get()
        aefa_process_message(election_message)
        if election_finished:
            print("election finished", flush=True)
            break


def aefa_process_message(message):
    global parent_node, candidate_leader, election_finished
    # todo: if received an election packet, send it to the neighbors but not to the parent
    # todo: until all the neighbors returned ACK message back, wait.
    # todo: if there is no neighbor to send the packet except the parent, then return ACK message
    # todo: when all neighbors/children sent back ACK message to the parent, return ACK message
    # todo: if parent is null, then it means it is the one that initiated the ELECTION.
    # todo: once initiator received ACK messages, inform all the nodes about LEADER
    message_type = message.type[1]
    print("$$$$$$This message is received: {} $$$$$$".format(message), flush=True)
    if message_type == "ELECTION":
        # todo: can we support asynchronous election?
        # todo: what if we continue with the election that has been started by the min/max identifier.
        if not parent_node:
            parent_node = message.name
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
            if parent_node != name_self:
                message_to_send = aefa_generate_message("ACK", parent_node)
                network_layer_queue.put(pickle.dumps(message_to_send))
    elif message_type == "ACK":
        # todo: check whether all neighbors returned ACK or not.
        # todo: if so, return ACK to the parent.
        # todo: if there is no parent, then declare the leader.
        neighbor_list_acknowledges[message.name] = True
        received_all_acks = True
        candidate_leader = message.name if message.name > candidate_leader else candidate_leader
        for neighbor in neighbor_list_acknowledges:
            received_all_acks = received_all_acks and neighbor_list_acknowledges[neighbor]

        if received_all_acks:
            if parent_node != name_self:
                message_to_send = aefa_generate_message("ACK", parent_node, candidate_leader)
                network_layer_queue.put(pickle.dumps(message_to_send))
            else:
                # todo: you are the one that initiated the connection. Broadcast the LEADER messages.
                for node in neighbor_list:
                    if node != name_self:
                        message_to_send = aefa_generate_message("LEADER", node, candidate_leader)
                        network_layer_queue.put(pickle.dumps(message_to_send))
    elif message_type == "LEADER":
        # todo: leader message is received. now you can measure the time.
        # todo: terminate if you want to. this is the end of the algorithm.
        # todo: flood leader packets just like ack packages.
        candidate_leader = message.message
        for node in neighbor_list:
            if node != parent_node:
                message_to_send = aefa_generate_message("LEADER", node, candidate_leader)
                network_layer_queue.put(pickle.dumps(message_to_send))

        print("########LEADER######## is : {}".format(message.message), flush=True)
        # election_finished = True


def aefa_generate_message(message_type, destination, message_info=""):
    message = packet(["AEFA", message_type], "", "", "", {}, destination, "", "", message_info, time.time(), 0)
    return message


def get_message_to_send():
    # get a message from user and send it
    # commit
    while True:
        command = input("command (auto or manual or elect): ")
        if command == "auto":
            get_messages_from_file()
        elif command == "manual":
            message = input("message: ")
            destination = input("destination: ")

            packet_to_send = packet("DATA", "", "", "", {}, destination, "", "", message, time.time(), 0)
            network_layer_queue.put(pickle.dumps(packet_to_send))
        else:
            commands = command.split()
            if commands[0] == "elect":
                start_election(commands[1])


def get_messages_from_file():
    input_file = open("input_" + name_self + ".txt", "r")
    commands = input_file.read().splitlines()
    for command in commands:
        message, destination = command.split(" ")
        packet_to_send = packet("DATA", "", "", "", {}, destination, "", "", message, time.time(), 0)
        print("packet: ", packet_to_send)
        network_layer_queue.put(pickle.dumps(packet_to_send))
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
        print("A->N", pickle.loads(message_raw))
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
            # print(message)
            if message.type == "neighbor":
                neighbor_list = message.link_state[name_self]
                print("neighbor list: ", neighbor_list)
            elif message.type == "topology":
                topology_table = message.link_state[name_self]
            else:
                election_queue.put(message)
        elapsed_time = time.time() - message.timestamp
        # print("\n (Application Layer) message \"%s\" received from %s within %f seconds in %d hops" %
        #       (message.message, message.name, elapsed_time, message.hop_count + 1), flush=True)
        time_file.write("%s %d %f\r\n" % (message.name, message.hop_count + 1, elapsed_time))
        # break on some condition


if __name__ == "__main__":
    context = zmq.Context()
    signal.signal(signal.SIGINT, signal_handler)

    read_config_file("config.ini", sys.argv[1])

    election_thread = threading.Thread(target=elect, args=())
    prompt_thread = threading.Thread(target=get_message_to_send, args=())
    network_layer_informer_thread = threading.Thread(target=network_layer_informer, args=())
    network_layer_listener_thread = threading.Thread(target=network_layer_listener, args=())

    election_thread.start()
    prompt_thread.start()
    network_layer_informer_thread.start()
    network_layer_listener_thread.start()

    election_thread.join()
    prompt_thread.join()
    network_layer_informer_thread.join()
    network_layer_listener_thread.join()
