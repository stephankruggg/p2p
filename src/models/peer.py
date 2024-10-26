import struct
import socket
import threading
import math

from utils.files_reader import read_topology_file, read_config_file, read_file_metadata
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

    def __str__(self):
        neighbors = '. '.join([str(n) for n in self._neighbors])
        return f'Peer {self._id} ready: {self._address}, {self._udp_port}, {self._speed}. {neighbors}'

    @property
    def id(self):
        return self._id

    @property
    def neighbors(self):
        return self._neighbors

    @property
    def udp_server(self):
        return self._udp_server

    def speed(self):
        with self._active_tcp_connections_lock:
            if self._active_tcp_connections == 0:
                return self._speed

            return math.floor(self._speed / (self._active_tcp_connections + 1))

    def _fetch_config_info_and_create_neighbors(self, config_components):
        self._neighbors = []

        for comp in config_components:
            if comp['id'] == self._id:
                self._address, self._udp_port, self._speed = comp['address'], comp['udp_port'], comp['speed']
                continue

            del comp['speed']
            self._neighbors.append(Neighbor(*comp.values()))

    def _create_udp_server(self):
        self._udp_server = UDPServer(self._address, self._udp_port, self)
        self._udp_server.start()

    def run(self, metadata_file):
        if not self._verify_metadata_file_validity(metadata_file):
            return

        requested_file, chunks, ttl = read_file_metadata(self._id, metadata_file)
        if not self._verify_file_need(requested_file):
            return

        self._create_file_buffer(chunks, requested_file)

        if self._verify_all_chunks_present_locally(requested_file):
            return

        client = self._flooding_client(ttl, requested_file)
        client.start()
        client.join()

        if self._verify_file_unretrievable():
            return

        fetching_technique = self._choose_fetching_technique()
        if fetching_technique == 'chunks':
            grouped_chunks = self._group_chunks_by_address_and_port()

            semaphore = threading.Semaphore(Constants.MAX_TCP_CLIENTS)
            clients = []

            for address_and_port, chunks in grouped_chunks.items():
                print('Waiting for all chunks to be fetched!')

                semaphore.acquire()

                tcp_client = self._create_tcp_client(address_and_port, requested_file, chunks, semaphore)
                clients.append(tcp_client)
                tcp_client.start()

            for client in clients:
                client.join()

            self._create_full_file(requested_file)
        else:
            self._fetch_full_file(requested_file)

            print('File downloaded!')

    def _verify_metadata_file_validity(self, metadata_file):
        peer_folder = Constants.FILES_PATH / str(self._id)
        filenames = [f.name for f in peer_folder.iterdir() if f.is_file()]

        if metadata_file not in filenames:
            print('Peer does not have this metadata file. Please save it locally and try again!')
            return False

        return True

    def _verify_file_need(self, requested_file):
        peer_folder = Constants.FILES_PATH / str(self._id)
        filenames = [f.name for f in peer_folder.iterdir() if f.is_file()]

        if requested_file in filenames:
            print('Peer already has this file!')
            return False

        return True

    def _create_file_buffer(self, chunks, requested_file):
        peer_folder = Constants.FILES_PATH / str(self._id)
        filenames = [f.name for f in peer_folder.iterdir() if f.is_file()]

        self._buffer = [None] * (chunks + 1)

        for c in range(chunks):
            chunk_name = requested_file + f'.ch{c}'

            if chunk_name in filenames:
                self._buffer[c] = {
                    'chunk': c,
                    'address': 'local',
                    'port': 'local',
                    'time': 0
                }

    def _verify_all_chunks_present_locally(self, requested_filename):
        if all(c is not None for c in self._buffer[:-1]):
            print('Peer has all chunks locally')
            self._create_full_file(requested_filename)
            return True

        return False

    def _flooding_client(self, ttl, requested_file):
        client_address = self._address
        client_port = Constants.UDP_CLIENT_PORT + self._id
        message = self._build_flooding_request(self._id, ttl, client_address, client_port, requested_file)

        return UDPClient(client_address, client_port, self._neighbors, self._buffer, message, requested_file, blocking = True)

    def _create_full_file(self, output_filename):
        peer_folder = Constants.FILES_PATH / str(self._id)

        with open(peer_folder / output_filename, 'wb') as of:
            for chunk in self._buffer[:-1]:
                with open(peer_folder / f"{output_filename}.ch{chunk['chunk']}", 'rb') as cf:
                    of.write(cf.read())

        print('Full file created!')

    def _build_flooding_request(self, id, ttl, client_address, client_port, filename):
        return struct.pack(Constants.FLOODING_REQUEST_FORMAT, ttl, id, socket.inet_aton(client_address), client_port, filename.encode('utf-8'))

    def _verify_file_unretrievable(self):
        if all(c is not None for c in self._buffer[:-1]) or self._buffer[-1] is not None:
            return False

        print('Cannot find full file!')
        return True

    def _choose_fetching_technique(self):
        chunk_fetching_time = float('inf')
        if all(c is not None for c in self._buffer[:-1]):
            chunk_fetching_time = sum(c['time'] for c in self._buffer[:-1])
        
        file_fetching_time = float('inf')
        if self._buffer[-1] is not None:
            file_fetching_time = self._buffer[-1]['time']

        if chunk_fetching_time >= file_fetching_time:
            return 'file'

        return 'chunks'

    def _group_chunks_by_address_and_port(self):
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

    def _fetch_full_file(self, filename):
        info = self._buffer[-1]

        tcp_client = self._create_tcp_client(f"{info['address']} {info['port']}", filename, [])

        tcp_client.start()
        tcp_client.join()

    def _create_tcp_client(self, address_and_port, filename, chunks, semaphore = None):
        address, port = address_and_port.split(' ')
        port = int(port)

        return TCPClient(self, address, port, semaphore, filename, chunks)

    def reroute(self, ttl, client_id, client_address, client_port, filename):
        message = self._build_flooding_request(client_id, ttl, client_address, client_port, filename)

        neighbors = [n for n in self._neighbors if n.id != client_id]

        client = UDPClient(self._address, Constants.UDP_REROUTE_PORT + self._id, neighbors, None, message, filename)
        client.start()

    def create_tcp_server(self):
        if not self._tcp_server:
            self._tcp_port = Constants.TCP_SERVER_PORT + self._id
            self._active_tcp_connections = 0
            self._active_tcp_connections_lock = threading.Lock()
            self._tcp_server = TCPServer(self._address, self._tcp_port, self)
            self._tcp_server.start()

        return self._tcp_server

    def sending_time(self, size):
        return size // self.speed()

    def change_active_tcp_connections(self, change):
        with self._active_tcp_connections_lock:
            self._active_tcp_connections += change
