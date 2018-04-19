import zmq
from collections import namedtuple
import threading

packet = namedtuple("packet", ["type", "source", "destination", "next_hop", "position", "message"])


def get_message_to_send(context):
    client_socket = context.socket(zmq.REQ)
    # get a message from user and send it
    while True:
        input_string = input("message dest: ")
        message, destination = input_string.split(" ")
        packet_to_send = packet("DATA", None, destination, None, None, message)
        client_socket.send(packet_to_send)


if __name__ == "__main__":
    context = zmq.Context()
    server_socket = context.socket(zmq.REP)
    server_socket.bind("tcp://*:5555")
    send_thread = threading.Thread(target=get_message_to_send, args=(context,))
    send_thread.start()

    while True:
        received_message = server_socket.recv()
        # process received message here
        print(received_message)
        # break on some condition

    send_thread.join()
