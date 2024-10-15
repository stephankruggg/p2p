from utils.constants import Constants

def read_topology_file(id: int) -> list[int]:
    if id < 0:
        return []

    with open(Constants.FILES_PATH / str(id) / 'topologia.txt', 'r') as f:
        for l in f:
            header, body = l.split(':')

            if id != int(header.strip()):
                continue

            return [int(n.strip()) for n in body.split(',')]
    
    return []

def read_config_file(ids: list[int]) -> list[dict]:
    if len(ids) == 0:
        return []

    components = []
    with open(Constants.FILES_PATH / str(ids[0]) / 'config.txt', 'r') as f:
        for l in f:
            for id in ids:
                header, body = l.split(':')

                header = int(header.strip())
                if id != int(header):
                    continue

                body = body.strip().split(',')
                if len(body) != 3:
                    continue

                components.append({
                    'id': header,
                    'address': str(body[0]),
                    'udp_port': int(body[1]),
                    'speed': int(body[2])
                })

    return components

def read_file_metadata(id, metadata_filename):
    contents = []

    with open(Constants.FILES_PATH / str(id) / f'{metadata_filename}', 'r') as f:
        for i, l in enumerate(f.readlines()):
            if i == 0:
                contents.append(l.strip())
            else:
                contents.append(int(l))

    return contents
