import sched
import threading
import yaml
import socket
import time
import re
from threading import Thread
import queue


def read_raw_message(raw_data: bytes) -> tuple:
    """Splits the message header from the data bytes of the message.

    :param raw_data: Full UDP packet
    :type raw_data: bytes
    :raises ValueError: When there header line is not present.
    :return: (Header, Data bytes)
    :rtype: Tuple
    """
    for i in range(len(raw_data)):
        if raw_data[i] == ord("\n"):
            return raw_data[0:i].decode("utf-8"), raw_data[i + 1 :]
    raise ValueError("Unable to find the end of line")


def read_message(raw_data: bytes):
    """Reads a UDP raw message, split the metadata, and decode data.

    :param raw_data: Raw UDP packet
    :type raw_data: bytes
    :return: Metadata and decoded data required for packet reassembly.
    :rtype: tuple
    """
    header, data = read_raw_message(raw_data)
    #'device/endpoint:encoding:id:sequence'
    match = re.search("(.*?)/(.*?):(.*?):(.*?):(.*?):(.*)", header)
    device = match[1]
    endpoint = match[2]
    encoding = match[3]
    id = match[4]
    sequence = match[5]
    max_sequence = match[6]
    if encoding == "yaml":
        decoded_data = yaml.load(data.decode("utf-8"), Loader=yaml.Loader)
    else:
        decoded_data = data
    return (
        device,
        endpoint,
        decoded_data,
        encoding,
        int(id),
        int(sequence),
        int(max_sequence),
    )


def build_message(
    device_name: str, endpoint: str, data, encoding: str, id=0, max_size=1000
):
    """Prepare the individual UDP packets required to send a message.

    :param device_name: Device Name
    :type device_name: str
    :param endpoint: Endpoint
    :type endpoint: str
    :param data: Data to transmit. Can be raw bytes or a python object to be encoded.
    :type data: bytes or object
    :param encoding: If an object is to be transmittted, encoding must be specified. YAML is the default encoding.
    :type encoding: str
    :param id: Packet sequence identifier, defaults to 0
    :type id: int, optional
    :param max_size: Maximum UDP payload size, defaults to 1000
    :type max_size: int, optional
    :raises ValueError: When the data type to transmit is not supported.
    :return: List of UDP messages
    :rtype: list
    """
    messages = []
    if encoding == "yaml":
        encoded_data = bytes(yaml.dump(data), "utf-8")
    elif encoding == "binary":
        encoded_data = data
    else:
        raise ValueError(
            "Please specify a supported encoding methods. (binary or yaml)"
        )
    number_of_messages = int(len(encoded_data) / max_size) + 1
    if len(encoded_data) % max_size == 0:
        number_of_messages -= 1

    remaining_bytes = len(encoded_data)

    for sequence in range(number_of_messages):
        header = bytes(
            f"{device_name}/{endpoint}:{encoding}:{id}:{sequence}:{number_of_messages}\n",
            "utf-8",
        )
        size = len(header) + min(remaining_bytes, max_size)
        message = bytearray(size)
        message[0 : len(header)] = header
        message[len(header) : size] = encoded_data[
            sequence * max_size : sequence * max_size + min(remaining_bytes, max_size)
        ]
        remaining_bytes = remaining_bytes - max_size
        messages.append(message)
    return messages


class Device:
    """Objects that represent a device."""

    def __init__(self, name, addr):
        self.name = name
        self.addr = addr
        self.broadcast = False
        self.enabled = True
        # self.rtcom = rtcom
        self.endpoints = {}

    def __getitem__(self, key):
        return self.endpoints[key].data

    def __contains__(self, key):
        return key in self.endpoints


class Endpoint:
    """Object that represent an endpoint."""

    def __init__(self, name, encoding, data=None):
        self.name = name
        self.encoding = encoding
        self.data = data
        self.next_data = {}
        self.transmission_id = -1  # Current transmission id


class RealTimeCommunication:
    """Handles the RealTimeCommunication."""

    def __init__(self, device_name=None, listen=True):
        """[summary]

        :param device_name: Name of the device. Will be used for other device to identify this one, defaults to hostname.
        :type device_name: [str], optional
        :param listen: Make this object the listen thread. There can only be one listener for now, defaults to True
        :type listen: bool, optional
        """
        if device_name is None:
            self.device_name = socket.gethostname()
        else:
            self.device_name = device_name
        try:
            addr = socket.gethostbyname(self.device_name)
        except:
            addr = "127.0.0.1"

        self.listen = listen

        self.this_device = Device(self.device_name, addr)
        self.message_queue = queue.Queue()

        self.endpoints = {}
        self.subscriptions = {}
        self.subscribers = {}

        self.heartbeat = 0
        self.write = True
        #  self.devices = {}

        if listen:
            self.listen_thread = RealTimeCommunicationListener(self)
            self.listen_thread.start()

    @property
    def devices(self):
        return self.listen_thread.devices

    def __getitem__(self, key):
        return self.listen_thread.devices[key]

    def __enter__(self):
        return self

    def __contains__(self, key):
        return key in self.listen_thread.devices

    def announce(self):
        message = {
            "announce": {"device_name": self.device_name, "endpoints": self.endpoints}
        }
        self.broadcast(message)

    def broadcast(self, packets, port=5999, addr=None):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
        if addr is None:
            addr = "255.255.255.255"
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for data in packets:
            sock.sendto(data, (addr, port))
        sock.close()

    def subscribe(self, target_device, endpoint):
        if target_device not in self.subscriptions:
            self.subscriptions[target_device] = {}
        self.subscriptions[target_device][endpoint] = True

    def get_subscribers(self):
        subscribers = {}
        for device_name in self.listen_thread.devices:
            device = self.listen_thread.devices[device_name]
            if "meta" in device and self.device_name in device["meta"]["subscribtions"]:
                subscribtions = device["meta"]["subscribtions"][self.device_name]
                for endpoint in subscribtions:
                    if endpoint not in subscribers:
                        subscribers[endpoint] = []
                    subscribers[endpoint].append(device_name)
        self.subscribers = subscribers
        return self.subscribers

    # def broadcast_endpoint(self, endpoint, data, encoding="yaml", addr=None):
    def _broadcast_endpoint(
        self, endpoint, data, encoding="yaml", addr=None, test_id_override=None
    ):
        if endpoint not in self.endpoints:
            self.endpoints[endpoint] = 0
        else:
            self.endpoints[endpoint] += 1
        packet_id = self.endpoints[endpoint]
        if test_id_override is not None:
            packet_id = test_id_override
        packets = build_message(
            self.device_name, endpoint, data, encoding, id=packet_id
        )

        if endpoint in self.subscribers:
            for device_name in self.subscribers[endpoint]:
                addr = self.listen_thread.devices[device_name].addr[0]
                self.broadcast(packets, addr=addr)
        else:
            self.broadcast(packets)

    def broadcast_endpoint(
        self, endpoint, data, encoding="yaml", addr=None, synchronous=False
    ):
        if not synchronous:
            self.message_queue.put((endpoint, data, encoding, addr))
        else:
            self._broadcast_endpoint(endpoint, data, encoding, addr)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.listen:
            self.listen_thread.enabled = False
            self.listen_thread.join()


class RealTimeCommunicationWriter(threading.Thread):
    def __init__(self, rtcom):
        threading.Thread.__init__(self)
        self.rtcom = rtcom
        self.enabled = True

    def run(self):
        while self.enabled:
            next_message = self.rtcom.message_queue.get()
            self.rtcom._broadcast_endpoint(*next_message)


class RealTimeCommunicationListener(threading.Thread):
    def __init__(self, rtcom, port=5999, hostname=None):
        threading.Thread.__init__(self)
        if hostname is None:
            UDP_IP = "0.0.0.0"
        print(f"Listening to {UDP_IP}")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.bind((UDP_IP, port))
        self.sock.setblocking(False)
        self.sock.settimeout(0.01)
        self.data_dict = None
        self.enabled = True
        self.miss_counter = 0
        self.rtcom = rtcom
        self.devices = {}
        self.heartbeat = 0
        self.last_meta_timestamp = 0

    def write(self):
        try:
            while True:
                next_message = self.rtcom.message_queue.get_nowait()
                self.rtcom._broadcast_endpoint(*next_message)
        except queue.Empty:
            # Broadcast device metadata.
            # TODO: Refactor
            meta = {}
            meta["heartbeat"] = self.heartbeat
            meta["subscribtions"] = self.rtcom.subscriptions
            if time.time() > self.last_meta_timestamp + 0.1:
                self.rtcom.broadcast_endpoint("meta", meta)
                self.last_meta_timestamp = time.time()

    def run(self):
        while self.enabled:
            self.heartbeat += 1
            self.rtcom.get_subscribers()
            if self.rtcom.write:
                self.write()
            try:
                data, addr = self.sock.recvfrom(1500)  # buffer size is 1024 bytes
                # print(data,addr)
                (
                    device,
                    endpoint,
                    data,
                    encoding,
                    id,
                    sequence,
                    max_sequence,
                ) = read_message(data)
                if device not in self.devices:
                    self.devices[device] = Device(device, addr)

                if max_sequence == 1:
                    if endpoint not in self.devices[device].endpoints:
                        self.devices[device].endpoints[endpoint] = Endpoint(
                            endpoint, encoding, data
                        )
                    else:
                        if (
                            id
                            > self.devices[device].endpoints[endpoint].transmission_id
                        ) or (
                            abs(
                                self.devices[device].endpoints[endpoint].transmission_id
                                - id
                            )
                            > 10
                        ):
                            self.devices[device].endpoints[
                                endpoint
                            ].transmission_id = id
                            self.devices[device].endpoints[endpoint].data = data
                else:
                    # Handle big messages
                    if endpoint not in self.devices[device].endpoints:
                        self.devices[device].endpoints[endpoint] = Endpoint(
                            endpoint, encoding
                        )

                    if id != self.devices[device].endpoints[endpoint].transmission_id:
                        self.devices[device].endpoints[endpoint].next_data = {}
                        self.devices[device].endpoints[endpoint].transmission_id = id
                    self.devices[device].endpoints[endpoint].next_data[sequence] = data
                    ready = True
                    for i in range(0, max_sequence):
                        if i not in self.devices[device].endpoints[endpoint].next_data:
                            ready = False
                            break
                    message_length = 0
                    if ready:
                        # print("ready")
                        input_buffer = bytearray(1000 * max_sequence)
                        for i in range(0, max_sequence):
                            data = self.devices[device].endpoints[endpoint].next_data[i]
                            input_buffer[i * 1000 : i * 1000 + len(data)] = data
                            message_length += len(data)
                        self.devices[device].endpoints[endpoint].data = input_buffer[
                            0:message_length
                        ]

                self.miss_counter = 0
                # print(f"{device}, {endpoint}, {encoding}, {id},{sequence}, {max_sequence}")
            except socket.timeout:
                self.miss_counter += 1
                time.sleep(0.01)
        self.sock.close()
