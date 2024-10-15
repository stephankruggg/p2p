import sys
import threading

from utils.files_reader import read_file_metadata
from models.peer import Peer
from utils.constants import Constants

# Todo: organize code, there is business logic spread throughout peer, main, udpserver, udpclient, tcpserver, tcpclient

def main():
    if len(sys.argv) < 2:
        print('Please provide an ID!')
        return

    id = int(sys.argv[1])
    peer = Peer(id)

    while True:
        metadata_file = input('Metadata file: ')

        if not peer.verify_metadata_file_validity(metadata_file):
            continue

        requested_file, chunks, ttl = read_file_metadata(peer.id, metadata_file)
        if not peer.verify_file_need(requested_file):
            continue

        peer.create_file_buffer(chunks, requested_file)

        if peer.verify_all_chunks_present_locally(requested_file):
            continue

        client = peer.flooding_client(ttl, requested_file)
        client.start()
        client.join()

        if peer.verify_file_unretrievable():
            continue

        fetching_technique = peer.choose_fetching_technique()
        if fetching_technique == 'chunks':
            grouped_chunks = peer.group_chunks_by_address_and_port()

            semaphore = threading.Semaphore(Constants.MAX_TCP_CLIENTS)
            clients = []

            for address_and_port, chunks in grouped_chunks.items():
                print('Waiting for all chunks to be fetched!')

                semaphore.acquire()

                tcp_client = peer.create_tcp_client(address_and_port, chunks, semaphore)
                clients.append(tcp_client)
                tcp_client.start()

            for client in clients:
                client.join()

            peer.create_full_file(requested_file)
        else:
            peer.fetch_full_file()

            print('File downloaded!')

if __name__ == '__main__':
    main()
