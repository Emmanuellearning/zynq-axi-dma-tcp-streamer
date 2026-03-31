import socket
import time

SERVER_IP = "192.168.1.10"
PORT = 7

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((SERVER_IP, PORT))

print("Connected")

buffer = b''
samples = 0
start = time.time()

while True:

    data = sock.recv(4096)
    buffer += data

    while len(buffer) >= 8:
        buffer = buffer[8:]
        samples += 1

    now = time.time()

    if now - start >= 1.0:
        print("Sampling Rate:", samples, "samples/sec")
        samples = 0
        start = now