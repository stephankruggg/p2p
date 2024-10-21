import sys

from models.peer import Peer


def main():
    if len(sys.argv) < 2:
        print('Please provide an ID!')
        return

    id = int(sys.argv[1])
    peer = Peer(id)

    while True:
        metadata_file = input('Metadata file: ')

        peer.run(metadata_file)

if __name__ == '__main__':
    main()
