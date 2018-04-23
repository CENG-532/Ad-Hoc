import math

name_self = "D"

known_nodes = ["A", "B", "C", "D", "E"]

topology_table = {"A": {"position": (0, 0), "ip_address": "A_IP", "neighbor_list": ["E"]},
                  "B": {"position": (10, 10), "ip_address": "B_IP", "neighbor_list": ["E", "D"]},
                  "C": {"position": (20, 20), "ip_address": "C_IP", "neighbor_list": ["D"]},
                  "D": {"position": (15, 15), "ip_address": "D_IP", "neighbor_list": []},
                  "E": {"position": (5, 5), "ip_address": "E_IP", "neighbor_list": ["A", "B"]}}

routing_table = {}

next_hop_table = {}

communication_range = 10

ip_address_self = "D_IP"


def calculate_distance(pos1, pos2):
    result = math.sqrt(math.pow(pos1[0] - pos2[0], 2) + math.pow(pos1[1] - pos2[1], 2))
    if communication_range < result:
        return math.inf
    return result


def find_shortest_path():
    global routing_table
    global topology_table_changed

    # dijkstra shortest-path algorithm
    routing_table[name_self] = {"dest_addr": ip_address_self, "next_hop": ip_address_self, "distance": 0}
    self_position = topology_table[name_self]["position"]
    p = [name_self]

    for x in known_nodes:
        pos_x = topology_table[x]["position"]
        if x is not name_self:
            routing_table[x] = {}
            if x in topology_table[name_self]["neighbor_list"]:
                routing_table[x]["distance"] = calculate_distance(self_position, pos_x)
                routing_table[x]["next_hop"] = topology_table[x]["ip_address"]
            else:
                routing_table[x]["distance"] = math.inf
                routing_table[x]["next_hop"] = -1

    while list(set(known_nodes) - set(p)):
        min_node = None
        for node in list(set(known_nodes) - set(p)):
            if min_node is None:
                min_node = node
            elif routing_table[min_node]["distance"] > routing_table[node]["distance"]:
                min_node = node
        if min_node is None:
            break
        p.append(min_node)
        pos_min_node = topology_table[min_node]["position"]
        for neighbor in list(set(topology_table[min_node]["neighbor_list"]) - set(p)):
            pos_neighbor = topology_table[neighbor]["position"]
            distance = calculate_distance(pos_min_node, pos_neighbor) + routing_table[min_node]["distance"]
            if round(distance, 2) < round(routing_table[neighbor]["distance"], 2):
                routing_table[neighbor]["distance"] = distance
                routing_table[neighbor]["next_hop"] = routing_table[min_node]["next_hop"]

    topology_table_changed = False


find_shortest_path()

print("top:", topology_table)
print("----------------------------")
print("routing:", routing_table)
