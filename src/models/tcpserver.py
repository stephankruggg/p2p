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
        self._speed = self._peer.speed

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((self._address, self._port))

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
            number_of_chunks = struct.unpack(Constants.CHUNKS_REQUEST_INITIAL_FORMAT, data[:1])[0]

            chunk_data = struct.unpack(f'{number_of_chunks * 255}s', data[1:])[0]
            chunks = [chunk_data[i:i+255].rstrip(b'\x00').decode('utf-8') for i in range(0, len(chunk_data), 255)]

            print(f'TCP Server received request to send: Number of Chunks -> {number_of_chunks}, Chunks -> {chunks}')

            for i, c in enumerate(chunks):
                print(f'TCP Server sending file: {c}')

                filepath = Constants.FILES_PATH / str(peer.id) / c
                with open(filepath, 'rb') as f:
                    while True:
                        bytes_to_read = peer.speed - 3
                        content = f.read(bytes_to_read)

                        if not content:
                            print(f'TCP reached EOF for file {c}.')
                            break

                        if '.ch' in c:
                            number = int(c.split('.ch')[1])
                            full_file = 0
                        else:
                            number = 0
                            full_file = 1

                        message = build_file_transfer_message(number, full_file, content)

                        print(f'TCP Server sending message: {message}')
                        connection.sendall(message)

                        time.sleep(1)
        except Exception as e:
            print(f'TCP Server -> An error occurred: {e}')
            traceback.print_exc()
        finally:
            socket.close()
            peer.change_active_tcp_connections(-1)
            print('TCP Server -> Connection closed!')

def build_file_transfer_message(number, full_file, content):
    return struct.pack(Constants.CHUNKS_RESPONSE_INITIAL_FORMAT, number, full_file) + content # Todo: We can send chunk number only once per chunk and have more throughput (for this we need 2 message types)
