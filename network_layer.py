import zmq
import threading
import queue  # I am not sure if we need a queue or not.

routing_table_mutex = threading.Lock()
# this is a dictionary that we can keep names to corresponding IPs, also necessary routing information.

routing_table = {}
# here define rooting algorithm

# here we need atomic data structure for rooting algorithm

# here we can use queues to communicate between two parts.


def periodic_update_location():
    pass


def find_routing():
    pass


def query_address():
    pass


def update_routing():
    pass


def inform_link_layer(message_from_app):
    pass


def inform_app_layer(message_from_link):
    # if the message contains control type flag, we should update the routing table we have.
    pass


class TemplateComm(threading.Thread):
    def __init__(self, server_address, client_address, zmq_context, operation):
        threading.Thread.__init__(self)
        self.server_socket = zmq_context.socket(zmq.REP)
        self.client_socket = zmq_context.socket(zmq.REQ)

        self.server_socket.bind(server_address)
        self.client_address = client_address

        self.task = operation

    def run(self):
        while True:
            message = self.server_socket.recv()

            # do operation depending on that message
            self.task(message)

            self.client_socket.send(message)


if __name__ == "__main__":
    context = zmq.Context()

    appLink = TemplateComm("tcp://network_layer:5555", "tcp://link_layer:5554", context, inform_link_layer)
    linkApp = TemplateComm("tcp://network_layer:5556", "tcp://app_layer:5557", context, inform_app_layer)
