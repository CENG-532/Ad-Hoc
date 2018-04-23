import zmq
import socket


udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

#  Do 10 requests, waiting each time for a response
for request in range(100):
    print("Sending request %s …" % request)
    udp_client.sendto(b"Hello", ("127.255.255.255", 5550))
