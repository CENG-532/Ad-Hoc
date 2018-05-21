import configparser
import math
from random import randint


communication_range = 10
start_point = [0, 0]
last_point = [0, 0]
generated_points = {}

link_str = "h{0} nohup python3 link_layer.py node{0} &\n"
network_str = "h{0} nohup python3 network_layer.py node{0} &\n"
app_str = "h{0} nohup python3 application_layer.py node{0} &\n"
config_str = "[node{0}]\n" \
             "positionX = {1}\n" \
             "positionY = {2}\n" \
             "ip = 10.0.0.{0}\n" \
             "network_layer_down_stream_address = tcp://127.0.0.1:5556\n" \
             "network_layer_up_stream_address = tcp://127.0.0.1:5555\n" \
             "link_layer_up_stream_address = tcp://127.0.0.1:5554\n" \
             "application_layer_address = tcp://127.0.0.1:5557\n\n"
topology_str = "host{0} = self.addHost('h{0}', ip='10.0.0.{0}', defaultRoute='via 10.0.0.1')\n"
topology_link_str = "self.addLink(host{0}, switch1, **linkopts)\n"


def generate_random_point(index, file_pointer, config_file, topology_file, topology_link_file):
    global last_point
    generated_x = randint(last_point[0], last_point[0] + 10)
    distance_x = last_point[0] - generated_x

    remaining_value = int(math.sqrt(math.pow(communication_range, 2) - math.pow(distance_x, 2)))

    while True:
        generated_y = randint(last_point[1], last_point[1] + remaining_value)
        if str(generated_x) + " " + str(generated_y) not in generated_points:
            generated_points[str(generated_x) + " " + str(generated_y)] = True
            last_point = [generated_x, generated_y]
            break

    file_pointer.write(link_str.format(index))
    file_pointer.write(network_str.format(index))
    file_pointer.write(app_str.format(index))

    config_file.write(config_str.format(index, str(generated_x), str(generated_y)))

    topology_file.write(topology_str.format(index))
    topology_link_file.write(topology_link_str.format(index))


def read_config(filename):
    global communication_range

    config = configparser.ConfigParser()
    config.read(filename)
    default_settings = config["DEFAULT"]
    communication_range = int(default_settings["range"])


def generate_point_cloud():
    file = open("generated.txt", "w")
    config_file = open("config_test.ini", "w")
    topology_file = open("topology_test.txt", "w")
    topology_link_file = open("topology_test_link.txt", "w")
    for i in range(2, 10):
        generate_random_point(i, file, config_file, topology_file, topology_link_file)


if __name__ == "__main__":
    read_config("config.ini")
    generate_point_cloud()
