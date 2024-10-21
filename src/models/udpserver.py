import threading
import socket
import struct
from time import sleep

from utils.constants import Constants

class UDPServer(threading.Thread):
    def __init__(self, address, port, peer):
        super().__init__()

        self._peer = peer
        self._address = address
        self._port = port

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind((self._address, self._port))

    @property
    def address(self):
        return self._address

    @property
    def address(self):
        return (self._address, self._port)

    def run(self):
        while True:
            print(f'UDP Server (Address: {self._address}, Port: {self._port}) listening...')

            data = self._socket.recv(1024)

            ttl, requester_id, requester_address, requester_port, requested_file = struct.unpack(Constants.FLOODING_REQUEST_FORMAT, data)
            requested_file = requested_file.rstrip(b'\x00').decode('utf-8')
            requester_address = socket.inet_ntoa(requester_address)
            print(f'Received request from ID -> {requester_id}, ADDRESS -> {requester_address}, PORT -> {requester_port}: TTL -> {ttl}, FILENAME -> {requested_file}')

            peer_folder = Constants.FILES_PATH / str(self._peer.id)
            files = [f for f in peer_folder.iterdir() if f.is_file()]
            chunks = {}
            entire_file = False
            entire_file_size = 0

            for f in files:
                filename = f.name
                if filename.startswith(requested_file):
                    size = f.stat().st_size
                    if filename == requested_file:
                        entire_file = True
                        entire_file_size = size

                        continue

                    chunks[filename] = size

            response = self._peer.flooding_response(chunks, entire_file, entire_file_size)
            self._socket.sendto(response, (requester_address, requester_port))

            ttl -= 1
            if ttl > 0:
                sleep(1)
                self._peer.reroute(ttl, requester_id, requester_address, requester_port, requested_file)
