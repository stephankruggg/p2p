import os
import threading
import socket
import struct
import shutil

from utils.constants import Constants

class TCPClient(threading.Thread):
    def __init__(self, peer, address, port, semaphore, filename, chunks):
        super().__init__()
        
        self._peer = peer

        self._server_address = address
        self._server_port = port
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self._semaphore = semaphore

        self._filename = filename
        self._message = self._build_chunks_request(chunks)

    def _build_chunks_request(self, chunks):
        chunk_number = len(chunks)
        message_format = Constants.CHUNKS_REQUEST_INITIAL_FORMAT + f'{chunk_number * 255}s'
        chunks = [c.encode('utf-8').ljust(255, b'\x00') for c in chunks]

        return struct.pack(message_format, chunk_number, b''.join(chunks))

    def run(self):
        print('TCP Client running...')

        self._socket.connect((self._server_address, self._server_port))
        self._socket.sendall(self._message)

        created_files = {}

        dirname = Constants.FILES_PATH / str(self._peer.id) / 'tmp'
        os.makedirs(dirname, exist_ok=True)

        while True:
            data = self._socket.recv(1024)
            if not data:
                break

            chunk_number, full_file = struct.unpack(Constants.CHUNKS_RESPONSE_INITIAL_FORMAT, data[:2])
            content = data[2:]

            if full_file:
                print(f'TCP Client received: Full file, Content -> {content}')
                file = self._filename
            else:
                print(f'TCP Client received: File number -> {chunk_number}, Content -> {content}')
                file = f'{self._filename}.ch{chunk_number}'

            filepath = dirname / file
            if chunk_number not in created_files.keys():
                created_files[chunk_number] = filepath

            with open(created_files[chunk_number], 'ab') as f:
                print(f'TCP Client saving content to file')
                f.write(content)

        for filepath in created_files.values():
            print(f'TCP Client moving file {filepath} out of tmp directory')
            shutil.move(filepath, Constants.FILES_PATH / str(self._peer.id))
            self._socket.close()

            if self._semaphore:
                self._semaphore.release()
