import math

name_self = "A"

distance_table = {}

known_nodes = [("A", (0, 0)), ("B", (2, 2)), ("C", (3, 3)), ("D", (4, 4))]

topology_table = {"link state": {"A": ["B", "C", "D"]}}

next_hop_table = {}

position_self = (0, 0)


def calculate_distance(pos1, pos2):
    return (math.sqrt(math.pow(pos1[0] - pos2[0], 2) + math.pow(pos1[1] - pos2[1], 2)))


def find_shortest_path():
    global position_self
    global next_hop_table
    global distance_table

    # dijkstra shortest-path algorithm
    next_hop_table = {"A": "A"}
    p = [(name_self, position_self)]
    distance_table[name_self] = 0
    for x, pos_x in known_nodes:
        if x is not name_self:
            if x in topology_table["link state"][name_self]:
                distance_table[x] = calculate_distance(position_self, pos_x)
                next_hop_table[x] = x  # paper says k instead of x
            else:
                distance_table[x] = math.inf
                next_hop_table[x] = -1  # paper says k instead of x

    print("next1", next_hop_table)
    is_changed = False
    while list(set(known_nodes) - set(p)):
        min_k, min_l, min_pos_k, min_pos_l = "", "", 0, 0  # most probably redundant
        for k, pos_k in list(set(known_nodes) - set(p)):
            min_distance = distance_table[k]
            for l, pos_l in p:
                distance = calculate_distance(pos_l, pos_k) + distance_table[l]
                if round(distance, 2) < round(min_distance, 2):
                    is_changed = True
                    min_distance = distance
                    min_k, min_pos_k, min_l, min_pos_l = k, pos_k, l, pos_l
            p.append((k, pos_k))
        if is_changed:
            is_changed = False
            distance_table[min_k] = min_distance
            next_hop_table[min_k] = next_hop_table[min_l]


find_shortest_path()
print("distance", distance_table)
print("known", known_nodes)
print("next", next_hop_table)
print("top", topology_table)
