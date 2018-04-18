import zmq

context =zmq.Context()

socket = context.socket(zmq.REP)

socket.bind("tcp://*:5555")