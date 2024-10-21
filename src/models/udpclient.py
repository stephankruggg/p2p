import threading
import socket
import struct
import re

from utils.constants import Constants

class UDPClient(threading.Thread):
    def __init__(self, client_address, client_udp_port, servers, buffer, message, filename, blocking = False):
        super().__init__()

        self._address = client_address
        self._port = client_udp_port
        self._servers = servers
        self._buffer = buffer
        self._message = message
        self._filename = filename
        self._blocking = blocking

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind((self._address, self._port))
        self._socket.settimeout(Constants.UDP_CLIENT_TIMEOUT)

    def run(self):
        for s in self._servers:
            self._socket.sendto(self._message, s.address)

        if self._blocking:
            try:
                while True:
                    data, _ = self._socket.recvfrom(4096)

                    peer_id, tcp_address, tcp_port, full_file_present, full_file_time, number_of_chunks = struct.unpack(Constants.FLOODING_RESPONSE_INITIAL_FORMAT, data[:12])
                    tcp_address = socket.inet_ntoa(tcp_address)

                    chunks = {}
                    for i in range(12, len(data[12:]), 259):
                        chunk_time, chunk_name = struct.unpack(Constants.FLOODING_RESPONSE_CHUNK_FORMAT, data[i:i+259])
                        chunk_time = int(chunk_time)
                        chunk_name = chunk_name.rstrip(b'\x00').decode('utf-8')

                        chunks[chunk_name] = chunk_time

                    print(f'Received response from ID -> {peer_id}: TCP address -> {tcp_address}, TCP port -> {tcp_port}, Full file present -> {full_file_present}, Full file time -> {full_file_time}, Number of chunks -> {number_of_chunks}, Chunks -> {list(chunks.keys())}')
            
                    for chunk_name, chunk_time in chunks.items():
                        chunk_number = int(re.search(r'\.ch(\d+)', chunk_name).group(1))

                        if not self._buffer[chunk_number] or self._buffer[chunk_number]['time'] > chunk_time:
                            self._buffer[chunk_number] = {
                                'chunk': chunk_name,
                                'address': tcp_address,
                                'port': tcp_port,
                                'time': chunk_time
                            }

                    if full_file_present:
                        if not self._buffer[-1] or self._buffer[-1]['time'] > full_file_time:
                            self._buffer[-1] = {
                                'chunk': self._filename,
                                'address': tcp_address,
                                'port': tcp_port,
                                'time': full_file_time
                            }
            except socket.timeout:
                print('UDP Client timed out!')
            finally:
                self._socket.close()
