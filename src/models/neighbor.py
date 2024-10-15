class Neighbor:
    def __init__(self, id, address, udp_port):
        self._id = id
        self._address = address
        self._udp_port = udp_port

    def __str__(self):
        return f'Neighbor {self._id}: {self._address}, {self._udp_port}'

    @property
    def id(self):
        return self._id

    @property
    def address(self):
        return (self._address, self._udp_port)