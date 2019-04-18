import socket
import struct

def send_msg(sock, msg):
    # Prefix each message with a 4-byte length
    msg = struct.pack('>I', len(msg)) + msg
    sock.sendall(msg)

def recv_msg(sock):
    # read message length and unpack it into an int
    raw_msglen = recvall(sock, 4)

    if not raw_msglen:
        return None
    
    msglen = struct.unpack('>I', raw_msglen)[0]

    # read the message data
    return recvall(sock, msglen)

def recvall(sock, n):
    # helper fn to recv n bytes or return None if EOF is hit
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data
