""" Simple implementation of a FTP server program used for pedagogical
purposes. Current commands supported:
    get <filename>: retrieve the file specified by filename.
    put <filename>: send the file to the server specified by filename.
    cd <path>: change the current working directory to the specified path.
    ls: list the files in the current working directory in the server.
    pwd: get the parent working directory
"""
import socket
import protocol
import subprocess
import hashlib

class FTPServer:
    def __init__(self, port=12000):
        """ Initializes the server on specified port and creates a server
        socket. Calls the connect function to begin listening for incoming
        connections from a client.
        @param port: port to listen on
        """
        self.address = ('', port)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.connect()
        except socket.error as e:
            print(e)

    def __del__(self):
        self.server_socket.close()

    def connect(self):
        """ Bind the socket to the specified port and enable the server to
        accept connections.
        """
        self.server_socket.bind(self.address)
        self.server_socket.listen(1)
        try:
            self.start()
        except socket.error as e:
            print(e)

    def start(self):
        """ Main driver of the FTP server. Wait for a socket connection
        request and receive and process commands.
        """
        while True:
            # Listen for incoming connections
            client_socket, client_addr = self.server_socket.accept()
            print('Server connected to: {} on port {}'.format(
                client_addr[0], client_addr[1]))

            # Process commands
            while True:
                cmd = protocol.recv_msg(client_socket).decode()
                if cmd == 'put':
                    self.recv_file(client_socket)

                elif cmd == 'get':
                    filename = protocol.recv_msg(client_socket).decode()
                    data_port = protocol.recv_msg(client_socket).decode()
                    self.send_file(client_addr[0], int(data_port), filename)

                elif cmd == 'ls':
                    data_port = protocol.recv_msg(client_socket).decode()
                    self.list_files(client_addr[0], int(data_port))

                elif cmd == 'cd':
                    target_path = protocol.recv_msg(client_socket).decode()
                    self.change_dir(target_path)

                elif cmd == 'pwd':
                    data_port = protocol.recv_msg(client_socket).decode()
                    self.send_pwd(client_addr[0], int(data_port))

                elif cmd == 'exit':
                    break

            # Close the socket after exit command
            client_socket.close()

    def change_dir(self, path):
        """ Change directory to the one specified by the path.
        @param path: target directory
        """
        try:
            subprocess.os.chdir(path)
        except Exception as e:
            print(e)
            return

    def send_pwd(self, client_addr, ephem_port):
        """ Send the output of pwd to the client.
        @param client_addr: IP address of the client
        @param ephem_port: ephemeral socket port number
        """
        try:
            output = subprocess.Popen('pwd', stdout=subprocess.PIPE).communicate()[0]
        except subprocess.SubprocessError as e:
            print(e)
            return
        ephem_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ephem_sock.connect((client_addr, ephem_port))
        protocol.send_msg(ephem_sock, output)
        ephem_sock.close()

    def list_files(self, client_addr, ephem_port):
        """ Send the output of ls in the cwd to the client.
        @param client_addr: IP address of the client
        @param ephem_port: ephemeral socket port number
        """
        try:
            output = subprocess.Popen('ls', stdout=subprocess.PIPE).communicate()[0]
        except subprocess.SubprocessError as e:
            print(e)
            return
        ephem_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ephem_sock.connect((client_addr, ephem_port))
        protocol.send_msg(ephem_sock, output)
        ephem_sock.close()

    def send_file(self, client_addr, ephem_port, filename):
        """ Create an ephemeral socket, send ephemeral socket port, and
        send the file data to the requesting client.
        @param client_addr: IP address of the client
        @param ephem_port: ephemeral socket port number
        @param filename: name of file to send
        """
        if self.is_valid_file(filename):
            data = open(filename, 'rb').read()
        else:
            data = 'NXFILE'.encode()
            ephem_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ephem_sock.connect((client_addr, ephem_port))
            protocol.send_msg(ephem_sock, data)
            ephem_sock.close()
            return

        # Create ephemeral socket
        ephem_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ephem_sock.connect((client_addr, ephem_port))

        # Send file data to client
        print('Sending {} to {}'.format(filename, client_addr))
        try:
            protocol.send_msg(ephem_sock, filename.encode())
            protocol.send_msg(ephem_sock, data)

            md5_send = hashlib.md5(data).hexdigest()
            protocol.send_msg(ephem_sock, md5_send.encode()) # send md5 hash
        except Exception as e:
            print('Error: {}'.format(e))
            print('Unsuccessful transfer of {}'.format(filename))
            ephem_sock.close() 
            return
        print('Transfer complete.')
        ephem_sock.close()

    def recv_file(self, client_sock):
        """ Create an ephemeral socket, receive files from the client, and 
        store in the current working directory.
        @param client_sock: client socket to send ephemeral port number.
        """
        # Create ephemeral socket
        ephem_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ephem_sock.bind(('', 0)) # 0 = first available port
        ephem_sock.listen(1)

        # Send the ephemeral port number to client
        ephem_name = ephem_sock.getsockname()
        protocol.send_msg(client_sock, str(ephem_name[1]).encode())

        # Accept any incoming connections on the ephemeral socket
        conn, addr = ephem_sock.accept()

        # Receive the file and store in cwd.
        try:
            filename = protocol.recv_msg(conn).decode()
            print('Receiving {} from {}'.format(
                filename, client_sock.getsockname()[0]))
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
            print('Unsuccessful transfer.')
            return

        with open(filename, 'w') as outfile: # write data file to file
            outfile.write(filedata)
        print('Transfer complete.')

        # Close the ephemeral socket.
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
    server = FTPServer()
