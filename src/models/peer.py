import struct
import socket

from utils.files_reader import read_topology_file, read_config_file
from utils.constants import Constants
from models.neighbor import Neighbor
from models.udpserver import UDPServer
from models.tcpserver import TCPServer
from models.udpclient import UDPClient
from models.tcpclient import TCPClient

class Peer:
    def __init__(self, id):
        self._id = id

        neighbors_ids = read_topology_file(id)
        config_components = read_config_file([id, *neighbors_ids])

        self._fetch_config_info_and_create_neighbors(config_components)
        self._create_udp_server()

        self._tcp_server = None
        print(self)

    def _fetch_config_info_and_create_neighbors(self, config_components):
        self._neighbors = []

        for comp in config_components:
            if comp['id'] == self._id:
                self._address, self._udp_port, self._speed = comp['address'], comp['udp_port'], comp['speed']
                continue

            del comp['speed']
            self._neighbors.append(Neighbor(*comp.values()))

    def __str__(self):
        neighbors = '. '.join([str(n) for n in self._neighbors])
        return f'Peer {self._id} ready: {self._address}, {self._udp_port}, {self._speed}. {neighbors}'

    def _create_udp_server(self):
        self._udp_server = UDPServer(self._address, self._udp_port, self)
        self._udp_server.start()

    @property
    def id(self):
        return self._id

    @property
    def neighbors(self):
        return self._neighbors

    @property
    def udp_server(self):
        return self._udp_server

    @property
    def speed(self):
        return self._speed

    def verify_metadata_file_validity(self, metadata_file):
        peer_folder = Constants.FILES_PATH / str(self._id)
        filenames = [f.name for f in peer_folder.iterdir() if f.is_file()]

        if metadata_file not in filenames:
            print('Peer does not have this metadata file. Please save it locally and try again!')
            return False

        return True

    def verify_file_need(self, requested_file):
        peer_folder = Constants.FILES_PATH / str(self._id)
        filenames = [f.name for f in peer_folder.iterdir() if f.is_file()]

        if requested_file in filenames:
            print('Peer already has this file!')
            return False

        return True

    def create_file_buffer(self, chunks, requested_file):
        peer_folder = Constants.FILES_PATH / str(self._id)
        filenames = [f.name for f in peer_folder.iterdir() if f.is_file()]

        self._buffer = [None] * (chunks + 1)

        for c in range(chunks):
            chunk_name = requested_file + f'.ch{c}'

            if chunk_name in filenames:
                self._buffer[c] = {
                    'chunk': chunk_name,
                    'address': 'local',
                    'port': 'local',
                    'time': 0
                }

    def verify_all_chunks_present_locally(self, requested_filename):
        if all(c is not None for c in self._buffer[:-1]):
            print('Peer has all chunks locally')
            self.create_full_file(requested_filename)
            return True

        return False

    def create_full_file(self, output_filename):
        peer_folder = Constants.FILES_PATH / str(self._id)

        with open(peer_folder / output_filename, 'wb') as of:
            for chunk_name in self._buffer[:-1]:
                with open(peer_folder / chunk_name['chunk'], 'rb') as cf:
                    of.write(cf.read())

        print('Full file created!')

    def flooding_client(self, ttl, requested_file):
        client_address = self._address
        client_port = Constants.UDP_CLIENT_PORT + self._id
        message = self._build_flooding_request(self._id, ttl, client_address, client_port, requested_file)

        return UDPClient(client_address, client_port, self._neighbors, self._buffer, message, requested_file, blocking = True)

    def reroute(self, ttl, client_id, client_address, client_port, filename):
        message = self._build_flooding_request(client_id, ttl, client_address, client_port, filename)

        neighbors = [n for n in self._neighbors if n.id != client_id]

        client = UDPClient(self._address, Constants.UDP_CLIENT_PORT + self._id, neighbors, None, message, filename)
        client.start()

    def _build_flooding_request(self, id, ttl, client_address, client_port, filename):
        return struct.pack(Constants.FLOODING_REQUEST_FORMAT, ttl, id, socket.inet_aton(client_address), client_port, filename.encode('utf-8'))

    def flooding_response(self, chunks, entire_file):
        self._tcp_port = Constants.TCP_SERVER_PORT + self._id
        if not self._tcp_server:
            self._tcp_server = TCPServer(self._address, self._tcp_port, self)
            self._tcp_server.start()

        # Todo: estimate time for chunk and entire file based on concurrent connections
        return self._build_flooding_response(self._id, self._address, self._tcp_port, chunks, self._speed, entire_file, self._speed)

    def _build_flooding_response(self, id, server_address, server_port, chunks, chunk_speed, entire_file, entire_file_speed):
        chunk_number = len(chunks)
        response_message_format = Constants.FLOODING_RESPONSE_INITIAL_FORMAT + f'{chunk_number * 255}s'
        chunks = [c.encode('utf-8').ljust(255, b'\x00') for c in chunks]

        return struct.pack(
            response_message_format, id, socket.inet_aton(server_address), server_port, entire_file, entire_file_speed, chunk_speed, chunk_number, b''.join(chunks)
        )

    def verify_file_unretrievable(self):
        print(self._buffer)
        if all(c is not None for c in self._buffer[:-1]) or self._buffer[-1] is not None:
            return False

        print('Cannot find full file!')
        return True

    def choose_fetching_technique(self):
        print(self._buffer)
        chunk_fetching_time = float('inf')
        if all(c is not None for c in self._buffer[:-1]):
            chunk_fetching_time = sum(c['time'] for c in self._buffer[:-1])
        
        file_fetching_time = float('inf')
        if self._buffer[-1] is not None:
            file_fetching_time = self._buffer[-1]['time']

        if chunk_fetching_time >= file_fetching_time:
            return 'file'

        return 'chunks'

    def group_chunks_by_address_and_port(self):
        grouped_chunks = {}

        for c in self._buffer[:-1]:
            if c['address'] == 'local':
                continue

            address_and_port = f"{c['address']} {c['port']}"
            if address_and_port in grouped_chunks:
                grouped_chunks[address_and_port].append(c['chunk'])
            else:
                grouped_chunks[address_and_port] = [c['chunk']]

        return grouped_chunks

    def fetch_full_file(self):
        info = self._buffer[-1]

        tcp_client = self.create_tcp_client(f"{info['address']} {info['port']}", [info['chunk']])

        tcp_client.start()
        tcp_client.join()

    def create_tcp_client(self, address_and_port, chunks, semaphore = None):
        address, port = address_and_port.split(' ')
        port = int(port)

        return TCPClient(self, address, port, semaphore, chunks[0].split('.ch')[0], self._build_chunks_request(chunks))

    def _build_chunks_request(self, chunks):
        chunk_number = len(chunks)
        message_format = Constants.CHUNKS_REQUEST_INITIAL_FORMAT + f'{chunk_number * 255}s'
        chunks = [c.encode('utf-8').ljust(255, b'\x00') for c in chunks]

        return struct.pack(message_format, chunk_number, b''.join(chunks))
