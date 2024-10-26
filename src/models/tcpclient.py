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
        self._number_of_chunks = len(chunks)

        if self._number_of_chunks == 0:
            message_format = Constants.CHUNKS_REQUEST_INITIAL_FORMAT
            return struct.pack(message_format, self._number_of_chunks, self._filename.encode('utf-8').ljust(255, b'\x00'))
        
        message_format = Constants.CHUNKS_REQUEST_INITIAL_FORMAT + f'{self._number_of_chunks}I'
        return struct.pack(message_format, self._number_of_chunks, self._filename.encode('utf-8').ljust(255, b'\x00'), *chunks)

    def run(self):
        print('TCP Client running...')

        self._socket.connect((self._server_address, self._server_port))
        self._socket.sendall(self._message)

        created_files = {}

        dirname = Constants.FILES_PATH / str(self._peer.id) / 'tmp'
        os.makedirs(dirname, exist_ok=True)

        files_to_fetch = max(1, self._number_of_chunks)
        for _ in range(files_to_fetch):
            data = self._socket.recv(2)

            chunk_number, full_file = struct.unpack(Constants.CHUNKS_RESPONSE_FILE_SPECIFICATION_FORMAT, data)

            if full_file:
                print(f'TCP Client received specification: Full file')
                file = self._filename
            else:
                print(f'TCP Client received specification: Chunk number -> {chunk_number}')
                file = f'{self._filename}.ch{chunk_number}'

            filepath = dirname / file
            if chunk_number not in created_files.keys():
                created_files[chunk_number] = filepath

            with open(created_files[chunk_number], 'wb') as f:
                while True:
                    data = self._socket.recv(1024)
                    if data == b'\x00':
                        print('TCP Client received EOF')
                        break

                    print(f'TCP Client received: File Content -> {data}')

                    print('TCP Client saving content to file')
                    f.write(data)

        for filepath in created_files.values():
            print(f'TCP Client moving file {filepath} out of tmp directory')
            shutil.move(filepath, Constants.FILES_PATH / str(self._peer.id))
            self._socket.close()

            if self._semaphore:
                self._semaphore.release()
