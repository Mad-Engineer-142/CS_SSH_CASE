from __future__ import print_function
import os
import socket
import re

from ssh2.session import Session

class SSHClient:
    def __init__(self, host, port=22, username=None, private_key_path=None, password=None):
        self.host = host
        self.port = port
        self.username = username
        self.private_key_path = private_key_path
        self.password = password
        self.session = None
        self.working_path = None

    def connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))
        
        self.session = Session()
        self.session.handshake(sock)
        
        if self.private_key_path:
            self.authenticate_with_key()
        elif self.password:
            self.authenticate_with_password()
        else:
            raise ValueError("Must provide either password or private_key for authentication.")

    def authenticate_with_password(self):
        self.session.userauth_password(self.username, self.password)

    def authenticate_with_key(self):
        try:
            with open(self.private_key_path, 'r') as key_file:
                private_key = key_file.read()
        except Exception as e:
            raise ValueError(f"Error reading private key file: {str(e)}")

        self.session.userauth_publickey_fromfile(self.username, self.private_key_path)

    def execute_command(self, command):
        if self.working_path:
            command = f"cd {self.working_path} && {command}"

        channel = self.session.open_session()
        channel.execute(command)

        size, data = channel.read()
        while size > 0:
            output_lines = data.decode().split('\n')
            for line in output_lines:
                colored_output = self.parse_output(line)
                print(colored_output)
            size, data = channel.read()

        channel.send_eof()
        channel.wait_closed()

        # Get exit status
        print("Exit status:", channel.get_exit_status())

    def parse_output(self, output):
        # Color directories in blue
        output = re.sub(r'(\S+/)$', r'\033[1;34m\1\033[0m', output)

        # Check if a dot is present in the line
        if '.' in output:
            # Color files with extensions in green
            output = re.sub(r'(\S+\.\S+)$', r'\033[1;32m\1\033[0m', output)
        else:
            # Paint lines without a dot in blue
            output = f'\033[1;34m{output}\033[0m'

        # Add your custom parsing logic using regular expressions
        error_pattern = re.compile(r'Error|Exception', re.IGNORECASE)
        if error_pattern.search(output):
            return '\033[1;31m{}\033[0m'.format(output)  # Red color for errors
        else:
            return output



    def change_working_path(self, new_path):
        self.working_path = new_path

    def close(self):
        if self.session:
            self.session.disconnect()

if __name__ == "__main__":
    host = input("host> ")
    port = int(input("port> "))
    username = input("server username> ")
    private_key_path = input("path to private key (press Enter if with password)> ")#None#'/path/to/your/private_key'
    password = ''
    if private_key_path == '':
        password = input("password> ")  # or None if using key-based authentication

    ssh_client = SSHClient(host, port, username, private_key_path=private_key_path, password=password)
    try:
        ssh_client.connect()

        while True:
            command = input("Enter command (type 'exit' to quit): ")
            if command.lower() == 'exit':
                break
            elif command.startswith('cd '):
                ssh_client.change_working_path(command[3:])
                print(f"Changed working directory to: {command[3:]}")
            else:
                ssh_client.execute_command(command)
    finally:
        ssh_client.close()
