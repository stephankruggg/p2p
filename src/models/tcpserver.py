import os
import threading
import socket
import struct
import time
import traceback

from utils.constants import Constants

class TCPServer(threading.Thread):
    def __init__(self, address, port, peer):
        super().__init__()
        self._address = address
        self._port = port
        self._peer = peer

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((self._address, self._port))

    @property
    def address(self):
        return self._address

    @property
    def port(self):
        return self._port

    def run(self):
        self._socket.listen(3)

        while True:
            print(f'TCP Server (Address: {self._address}, Port: {self._port}) listening...')

            connection, address = self._socket.accept()
            
            print(f'TCP Server connected to: {address}')

            self._peer.change_active_tcp_connections(1)

            threading.Thread(target=transfer_files, args=(connection, self._peer, self._socket)).start()

def transfer_files(connection, peer, socket):
    print('TCP Server ready to send files...')

    with connection:
        try:
            data, _ = connection.recvfrom(4096)
            number_of_chunks, filename = struct.unpack(Constants.CHUNKS_REQUEST_INITIAL_FORMAT, data[:256])
            filename = filename.rstrip(b'\x00').decode('utf-8')

            if number_of_chunks == 0:
                print(f'TCP Server received request to send full file: Number of Chunks -> {number_of_chunks}, Filename -> {filename}')

                connection.sendall(build_file_declaration_message(0, 1))
                time.sleep(1)

                filepath = Constants.FILES_PATH / str(peer.id) / filename

                send_file(connection, peer, filepath, filename)
            else:
                chunks = list(struct.unpack(f'>{number_of_chunks}I', data[256:]))
                print(f'TCP Server received request to send chunks: Number of Chunks -> {number_of_chunks}, Filename -> {filename}, Chunks -> {chunks}')

                for c in chunks:
                    print(f'TCP Server sending file: Filename -> {filename}, Chunk -> {c}')

                    connection.sendall(build_file_declaration_message(c, 0))
                    time.sleep(1)

                    chunk_filename = f'{filename}.ch{c}'
                    filepath = Constants.FILES_PATH / str(peer.id) / chunk_filename

                    send_file(connection, peer, filepath, chunk_filename)
        except Exception as e:
            print(f'TCP Server -> An error occurred: {e}')
            traceback.print_exc()
        finally:
            socket.close()
            peer.change_active_tcp_connections(-1)
            print('TCP Server -> Connection closed!')

def build_file_declaration_message(number, full_file):
    return struct.pack(Constants.CHUNKS_RESPONSE_FILE_SPECIFICATION_FORMAT, number, full_file)

def send_file(connection, peer, filepath, filename):
    with open(filepath, 'rb') as f:
        while True:
            bytes_to_read = peer.speed()
            content = f.read(bytes_to_read)

            if not content:
                print(f'TCP reached EOF for file: {filename}.')
                connection.sendall(b'\x00')
                time.sleep(1)
                break

            print(f'TCP Server sending message: {content}')
            connection.sendall(content)

            time.sleep(1)
