from pathlib import Path

class Constants:
    FILES_PATH = Path('..') / 'example'

    TCP_SERVER_PORT = 4000
    UDP_REROUTE_PORT = 4100
    UDP_CLIENT_PORT = 5000

    MAX_TCP_CLIENTS = 2

    UDP_CLIENT_TIMEOUT = 20

    # TTL (1B), Peer ID (2B), Address (4B String), Port (2B), Filename (255B String)
    FLOODING_REQUEST_FORMAT = '!BH4sH255s'

    # Peer ID (2B), Address (4B String), Port (2B), Full File (1B), Full File Time (2B), Number of Chunks (1B)
    FLOODING_RESPONSE_INITIAL_FORMAT = '!H4sHBHB'

    # Chunk time (1B), Chunk name (255B String)
    FLOODING_RESPONSE_CHUNK_FORMAT = 'I255s'

    # Number of Chunks (1B)
    CHUNKS_REQUEST_INITIAL_FORMAT = '!B'

    # Chunk number (1B), Full File (1B)
    CHUNKS_RESPONSE_INITIAL_FORMAT = '!BB'
