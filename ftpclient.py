""" Simple implementation of a FTP client program used for pedagogical
purposes. Current commands supported:
    get <filename>: retrieve the file specified by filename.
    put <filename>: send the file to the server specified by filename.
    cd <path>: change the current working directory to the specified path.
    ls: list the files in the current working directory in the server.
    pwd: get the parent working directory
"""
import socket
import protocol
import argparse
import subprocess
import hashlib

class FTPClient:
    def __init__(self, host, port):
        """ Initializes the client socket for command connection and attempts to
        connect to the server specified by the host and port.
        @param host: server ip addr
        @param port: port to communicate on
        """
        self.host = host
        self.port = port
        self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Connect to server and start listener
        try:
            self.connect((self.host, self.port))
            self.start()
        except socket.error as e:
            print(e) # use logging later

    def __del__(self):
        self.client_sock.close()

    def connect(self, server):
        """ Establish a connection with the client socket
        @param server: tuple that contains the host IP and port.
        """
        self.client_sock.connect(server)

    def start(self):
        """ Main driver of the FTP client, which continuously parses any
        user args and calls the necessary member functions.
        """
        while True:
            tokens = self.parse() 
            cmd = tokens[0]
            
            if cmd == 'put' and len(tokens) == 2:
                filename = tokens[1]

                if self.is_valid_file(filename):
                    protocol.send_msg(self.client_sock, cmd.encode())
                    data_port = protocol.recv_msg(self.client_sock).decode()
                    self.send_file(filename, int(data_port))
                else:
                    print("File does not exist")

            elif cmd == 'get' and len(tokens) == 2:
                filename = tokens[1]
                protocol.send_msg(self.client_sock, cmd.encode())
                protocol.send_msg(self.client_sock, filename.encode())
                self.recv_file()

            elif cmd == 'ls' and len(tokens) == 1:
                protocol.send_msg(self.client_sock, cmd.encode())
                self.list_files()

            elif cmd == 'cd' and len(tokens) == 2:
                path = tokens[1]
                protocol.send_msg(self.client_sock, cmd.encode())
                protocol.send_msg(self.client_sock, path.encode())

            elif cmd == 'pwd' and len(tokens) == 1:
                protocol.send_msg(self.client_sock, cmd.encode())
                self.get_pwd()

            elif cmd == 'exit':
                protocol.send_msg(self.client_sock, cmd.encode())
                self.client_sock.close()
                break
            
    def parse(self):
        """ Asks for user input and parses the command to extract tokens.
        """
        tokens = input(">>> ").split(' ')
        return tokens

    def get_pwd(self):
        """ Receives the output of cwd from the server.
        """
        ephem_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ephem_sock.bind(('', 0))
        ephem_sock.listen(1)

        ephem_name = ephem_sock.getsockname()
        protocol.send_msg(self.client_sock, str(ephem_name[1]).encode())

        conn, addr = ephem_sock.accept()
        pwd_output = protocol.recv_msg(conn).decode()
        print(pwd_output)
        
        conn.close()
        ephem_sock.close()

    def list_files(self):
        """ Receives the output of ls in the cwd from the server.
        """
        # Create an ephemeral socket
        ephem_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ephem_sock.bind(('', 0))
        ephem_sock.listen(1)

        # Send the ephemeral port number to server
        ephem_name = ephem_sock.getsockname()
        protocol.send_msg(self.client_sock, str(ephem_name[1]).encode())

        # Accept any incoming connections on the ephemeral socket
        conn, addr = ephem_sock.accept()

        # Receive the ls output from server
        ls_output = protocol.recv_msg(conn).decode()
        print(ls_output)

        conn.close() # close the ephem socket conn
        ephem_sock.close()

    def send_file(self, filename, ephem_port):
        """ Create an ephemeral socket and send file.
        @param filename: path to the file to send.
        """
        data = open(filename, 'rb').read()

        ephem_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ephem_sock.connect((self.host, ephem_port))

        print('Sending {} to {}'.format(filename, self.host))

        try:
            protocol.send_msg(ephem_sock, filename.encode())
            protocol.send_msg(ephem_sock, data)

            # send md5 hash
            md5_send = hashlib.md5(data).hexdigest()
            protocol.send_msg(ephem_sock, md5_send.encode())
        except Exception as e:
            print('Error: {}'.format(e))
            print('Unsuccessful transfer of {}'.format(filename))
            ephem_sock.close() 
            return

        print('Transfer complete.')
        ephem_sock.close()

    def recv_file(self):
        """ Receive a file through an ephemeral socket from the client.
        """
        # Create ephemeral socket
        ephem_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ephem_sock.bind(('', 0))
        ephem_sock.listen(1)

        # Send the ephemeral port number to server
        ephem_name = ephem_sock.getsockname()
        protocol.send_msg(self.client_sock, str(ephem_name[1]).encode())

        # Accept any incoming connections on the ephemeral socket
        conn, addr = ephem_sock.accept()

        # Receive the file and store in cwd
        filename = protocol.recv_msg(conn).decode()
        if filename == 'NXFILE':
            print('File does not exist.')
        else:
            print('Receiving {} from {}'.format(filename, self.host))

            try:
                filedata = protocol.recv_msg(conn).decode()
                # Check file integrity
                md5_recv = protocol.recv_msg(conn).decode()
                md5_local = hashlib.md5(filedata.encode()).hexdigest()
                if md5_recv != md5_local:
                    print('Corrupt file data during transfer.')
                    return
            except Exception as e:
                print(e)
                print('Error receiving file {}'.format(filename))
                return

            with open(filename, 'w') as outfile:
                outfile.write(filedata)
            print('Transfer complete.')

        # Close the ephemeral socket
        conn.close()
        ephem_sock.close()

    def is_valid_file(self, filename):
        """ Checks if the path is valid and if the file exists.
        @param filename: name of file of file including path
        """
        if subprocess.os.path.exists(filename):
            return True
        return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("ip")
    args = parser.parse_args()
    client = FTPClient(args.ip, 12000)
