import zmq
import threading
import pickle
import signal
import sys
import configparser
import time
import queue
import subprocess
import os

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

election_requester = None

bully_wait_time = 3

bully_dict = {"ack": {"sent": [], "received": []},
              "elect": {"sent": [], "received": []},
              "grant": {"sent": [], "received": []},
              "victory": {"sent": [], "received": []}}

elect_start_time = 0

parent_node = None

candidate_leader = None

election_finished = False

election_algorithm = None
election_count = None
is_election_starter = None
is_election_auto = None
existing_nodes = {}  # dictionary [nodeName] -> [finished(boolean)]
local_election_count = 0


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
    global neighbor_list_acknowledges, parent_node, candidate_leader, election_requester, election_queue
    global election_finished
    election_finished = False
    neighbor_list_acknowledges = {}
    parent_node = None
    candidate_leader = name_self
    election_requester = None
    election_queue = queue.Queue()


def all_nodes_finished():
    global existing_nodes
    finished = True

    for node in existing_nodes:
        finished = finished and existing_nodes[node]
        if not finished:
            return False

    return True


def aefa(first_message, start):
    global parent_node, election_requester, elect_start_time, existing_nodes

    elapsed_time = None

    if start:
        aefa_start()

    else:
        aefa_process_message(first_message)

    while True:
        election_message = election_queue.get()
        aefa_process_message(election_message)
        if election_finished:
            print("election finished", flush=True)
            elapsed_time = time.time() - elect_start_time
            print("TIME: ", time.time() - elect_start_time)
            break

    if name_self == election_requester:
        for node in topology_table:
            if node != name_self:
                existing_nodes[node] = False

        while not all_nodes_finished():
            message = election_queue.get()
            message_headers = message.type
            if message_headers[1] == "FINISHED":
                print("node: {} is finished".format(message.name))
                existing_nodes[message.name] = True

        print("restarting election over again")
        kill_on_finish()

    else:
        message_to_send = aefa_generate_message("FINISHED", election_requester)
        network_layer_queue.put(pickle.dumps(message_to_send))

    time_file.write("{:.4f}\n".format(elapsed_time))
    print("elapsed time: {:.4f}".format(elapsed_time))
    elect()


def aefa_start():
    global parent_node, election_requester

    parent_node = name_self
    election_requester = name_self

    for neighbor in neighbor_list:
        message_time = aefa_generate_message("TIME", neighbor, name_self)
        network_layer_queue.put(pickle.dumps(message_time))

        message_elect = aefa_generate_message("ELECTION", neighbor, name_self)
        neighbor_list_acknowledges[neighbor] = False
        network_layer_queue.put(pickle.dumps(message_elect))


def aefa_stop(message_headers, message):
    global election_requester, parent_node, neighbor_list_acknowledges

    if election_requester < message_headers[0]:
        # todo: need to inform that election requester in the message should stop its election
        # message format: type=[STOP] message="[WRONG_REQUESTER] [CORRECT_REQUESTER]"
        message_to_send = aefa_generate_message("STOP", message.name,
                                                message_headers[0] + " " + election_requester)
        network_layer_queue.put(pickle.dumps(message_to_send))
    elif election_requester > message_headers[0]:
        print("ANOTHER ELECTION [{}] is going on. STOPPING CURRENT [{}]!".format(message_headers[0],
                                                                                 election_requester))
        # the identifier of other election requester is better, this node needs to stop its own election
        previous_election_requester = election_requester
        election_requester = message_headers[0]
        for neighbor in neighbor_list:
            message_to_send = aefa_generate_message("STOP", neighbor,
                                                    previous_election_requester + " " + election_requester)
            network_layer_queue.put(pickle.dumps(message_to_send))

        parent_node = message.name

        neighbor_list_acknowledges = {}


def aefa_process_message(message):
    global parent_node, candidate_leader, election_finished, election_requester, neighbor_list_acknowledges
    global elect_start_time
    # if received an election packet, send it to the neighbors but not to the parent
    # until all the neighbors returned ACK message back, wait.
    # if there is no neighbor to send the packet except the parent, then return ACK message
    # when all neighbors/children sent back ACK message to the parent, return ACK message
    # if parent is null, then it means it is the one that initiated the ELECTION.
    # once initiator received ACK messages, inform all the nodes about LEADER
    message_type = message.type[1]
    message_headers = message.message.split()  # 0 -> requester, 1 -> candidate

    print("$$$$$$This message is received: {} $$$$$$".format(message), flush=True)
    if message_type == "ELECTION":
        if not election_requester:
            election_requester = message_headers[0]
        else:
            aefa_stop(message_headers, message)

        if not parent_node:
            parent_node = message.name

        elif parent_node != message.name:
            aefa_stop(message_headers, message)

        aefa_election_inform_neighbors()
        # check for the neighbors.

    elif message_type == "ACK":
        if message_headers[0] != election_requester:
            # here we return because, ACK messages come from the wrong selection
            return

        if neighbor_list_acknowledges[message.name]:
            # duplicate ack messages
            return

        neighbor_list_acknowledges[message.name] = True
        received_all_acks = True
        candidate_leader = message_headers[1] if message_headers[1] > candidate_leader else candidate_leader

        for neighbor in neighbor_list_acknowledges:
            received_all_acks = received_all_acks and neighbor_list_acknowledges[neighbor]

        if received_all_acks:
            if parent_node != name_self:
                message_to_send = aefa_generate_message("ACK", parent_node, election_requester + " " + candidate_leader)
                network_layer_queue.put(pickle.dumps(message_to_send))
            else:
                print("Leader is selected: ", candidate_leader)
                for node in neighbor_list:
                    if node != name_self:
                        message_to_send = aefa_generate_message("LEADER", node,
                                                                election_requester + " " + candidate_leader)
                        network_layer_queue.put(pickle.dumps(message_to_send))
                election_finished = True
    elif message_type == "LEADER":
        # leader message is received. now you can measure the time.
        # flood leader packets just like ack packages.

        candidate_leader = message_headers[1]
        for node in neighbor_list:
            if node != parent_node:
                message_to_send = aefa_generate_message("LEADER", node, election_requester + " " + candidate_leader)
                network_layer_queue.put(pickle.dumps(message_to_send))

        print("########LEADER######## is : {}".format(candidate_leader), flush=True)
        election_finished = True

    elif message_type == "STOP":
        # message format = [previous requester] [new requester]
        election_requester_data = message_headers[1]
        if election_requester == election_requester_data:
            # we are already in the same election, ignore the message.
            pass
        elif election_requester > election_requester_data:
            print("ANOTHER ELECTION [{}] is going on. STOPPING CURRENT [{}]!".format(message_headers[1],
                                                                                     election_requester))
            # we need to spread STOP message to our neighbors but the sender.
            previous_election_requester = election_requester
            election_requester = election_requester_data
            for neighbor in neighbor_list:
                if neighbor != message.name:
                    message_to_send = aefa_generate_message("STOP", neighbor,
                                                            previous_election_requester + " " + election_requester)
                    network_layer_queue.put(pickle.dumps(message_to_send))

            neighbor_list_acknowledges = {}

            parent_node = message.name

        # aefa_election_inform_neighbors()

        else:
            # the stop requester should stop.
            pass
    elif message_type == "TIME":
        if not election_requester:
            election_requester = message_headers[0]
            parent_node = message.name
            elect_start_time = message.timestamp
        else:
            aefa_stop(message_headers, message)

        for neighbor in neighbor_list:
            if parent_node != neighbor:
                message_to_send = aefa_generate_message("TIME", neighbor, election_requester)
                network_layer_queue.put(pickle.dumps(message_to_send))


def aefa_election_inform_neighbors():
    global election_requester, candidate_leader, neighbor_list_acknowledges
    message_sent = False
    for neighbor in neighbor_list:
        if neighbor != parent_node:
            message_sent = True
            message_to_send = aefa_generate_message("ELECTION", neighbor, election_requester)
            neighbor_list_acknowledges[neighbor] = False
            network_layer_queue.put(pickle.dumps(message_to_send))
    if message_sent:
        return
    else:
        # no neighbor to inform about election.
        # return ACK message back to parent. if no parent exist, you are the only one in the network.
        # declare yourself as leader.
        if parent_node != name_self:
            message_to_send = aefa_generate_message("ACK", parent_node, election_requester + " " + candidate_leader)
            network_layer_queue.put(pickle.dumps(message_to_send))


def aefa_generate_message(message_type, destination, message_info=""):
    message = packet(["AEFA", message_type], "", "", "", {}, destination, "", "", message_info, elect_start_time, 0)
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


def kill_process_(node):
    child_link_layer = int(
        subprocess.check_output(["pgrep", '-f', "python3 link_layer.py " + node]).decode().split()[0])
    child_network_layer = int(
        subprocess.check_output(["pgrep", '-f', "python3 network_layer.py " + node]).decode().split()[0])
    child_application_layer = int(
        subprocess.check_output(["pgrep", '-f', "python3 application_layer.py " + node]).decode().split()[0])
    print("result of communicate", child_link_layer, child_network_layer, child_application_layer)
    os.kill(child_link_layer, signal.SIGTERM)
    os.kill(child_network_layer, signal.SIGTERM)
    os.kill(child_application_layer, signal.SIGTERM)


def kill_on_finish():
    for node in topology_table:
        if node != name_self:
            kill_process_(node)

    kill_process_(name_self)


def signal_handler(signal, frame):
    time_file.close()
    context.term()
    context.destroy()
    sys.exit()


def read_config_file(filename, name):
    global application_layer_address, network_layer_up_stream_address, name_self, time_file
    global election_algorithm, election_count, is_election_starter, is_election_auto
    config = configparser.ConfigParser()
    config.read(filename)

    name_self = name
    time_file = open("time" + name + ".txt", "w+")

    default_settings = config["DEFAULT"]

    election_algorithm = default_settings["election_algorithm"]
    election_count = int(default_settings["election_count"])
    is_election_starter = default_settings["election_starter"] == name
    is_election_auto = default_settings["election_test_type"] == "auto"

    print(election_count, election_algorithm, is_election_starter, is_election_auto)

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
    global existing_nodes
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
        # time_file.write("%s %d %f\r\n" % (message.name, message.hop_count + 1, elapsed_time))
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
    if not is_election_auto:
        prompt_thread.start()
    network_layer_informer_thread.start()
    network_layer_listener_thread.start()

    election_thread.join()
    if not is_election_auto:
        prompt_thread.join()
    network_layer_informer_thread.join()
    network_layer_listener_thread.join()
