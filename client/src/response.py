import struct
import logger
import os
from enum import Enum

class Status(Enum):
    FILES_RETREIVED = 210
    LIST_RETURNED = 211
    OPERATION_SUCCESS = 212
    FILE_NOT_FOUND = 1001
    EMPTY_DIRECTORY = 1002
    GENERAL_ERROR = 1003


class Response:
    # Response header format & size calculation
    HEADER_FORMAT = 'B H B I'  
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    # Constructor
    def __init__(self,socket):
        self.socket = socket
        self.hex_data = None
        self.version = None
        self.status = None
        self.name_len = None
        self.data_size = None
        self.name = None
        self.data = None

    # Helper function to receive exactly 'size' bytes
    def receive_all(self, size):
        data = bytearray()
        while len(data) < size:
            try:
                packet = self.socket.recv(size - len(data))
                if not packet:
                    raise ConnectionError("Connection closed prematurely by the server.")
                data.extend(packet)
                print(f"Received {len(data)}/{size} Bytes")
            except ConnectionError as e:
                print(f"Error: {e}")
                return;
        return data     

    # Parses the header message and inputs the data to respected holders
    def parse_header(self):
        header_data = self.receive_all(self.HEADER_SIZE)
        if not header_data:
            print(f"Failed to receive header data. Connection may have been closed or packet failed to arrive\n")
            self.status = None
            self.data_size = 0
            return
        try:
            self.hex_data = logger.format_hex(header_data,1)
            self.version, status_code ,self.name_len, self.data_size = struct.unpack(self.HEADER_FORMAT,header_data)
            self.status = Status(status_code) if status_code in Status._value2member_map_ else None
        except struct.error as e:
            print(f"Error: {e}")
            self.status = None
            self.data_size = 0

    # If we need to parse the file name
    def parse_name(self):
        if self.name is None and self.name_len > 0:
            data = bytearray()
            while len(data) < self.name_len:
                try:
                    packet = self.socket.recv(self.name_len - len(data))
                    if not packet:
                        raise ConnectionError("Connection closed prematurely by the server.")
                    data.extend(packet)
                    print(f"Received {len(data)}/{self.name_len} Bytes")
                except ConnectionError as e:
                    print(f"Error: {e}")
                    return;
            self.name = data

    # Parses all the data
    def parse_data(self):
        if self.data is None and self.data_size > 0:
            data = bytearray()
            while len(data) < self.data_size:
                try:
                    packet = self.socket.recv(self.data_size - len(data))
                    if not packet:
                        raise ConnectionError("Connection closed prematurely by the server.")
                    data.extend(packet)
                    print(f"Received {len(data)}/{self.data_size} Bytes")
                except ConnectionError as e:
                    print(f"Error: {e}")
                    return;
            self.data = data 

    def get_data(self):
        return self.data

    def reset_data(self):
        self.data = None

    def get_status(self):
        return Status(self.status)

    def get_name(self):
        return self.name

    # Prints the self.data field
    def print_data(self):
        try:
            decoded_data = self.get_data().decode('utf-8') if self.get_data() is not None else "No data"
            return decoded_data
        except UnicodeDecodeError:
            return f"Raw data (hex): {self.get_data().hex()}"
    
    # Prints the self.file_name field
    def print_name(self):
        try:
            decoded_data = self.get_name().decode('utf-8') if self.get_name() is not None else "No Name"
            return decoded_data
        except UnicodeDecodeError:
            return f"Raw data (hex): {self.get_name().hex()}"

    # Custom call method
    def __str__(self):
        # Parse the header
        self.parse_header()
        header = (f"Response Received: \n"
                f"{self.hex_data}\n"
                f"Version: {self.version}")

        status_str = self.status.name if self.status else "UNKNOWN_STATUS"

        # Parse the Name related fields
        self.parse_name()
        file_name = self.print_name()

        # Parse the data related fields
        self.parse_data()
        data_received = self.print_data()
        if self.status is Status.FILES_RETREIVED:
            # File name is unique_name (retreived file with incremented (1) if already exists),
            # unclear if should be tmp or not...
            # We also need it to be the same type, so it is best to keep the name with the same extension
            unique_name = unique_file_name(file_name)
            # Write to the file as long as there is data to be written
            with open(unique_name,'w',newline='\n') as file:
                file.write(data_received)

            # Print a different message.
            return (f"{header}\n"
                f"Status: {status_str}\n"
                f"Name Length: {self.name_len} Bytes\n"
                f"File Name: {file_name}\n"
                f"Data Size: {self.data_size} Bytes\n"
                f"Data Written to file {unique_name}\n")

        # Construct the full response string and return it
        return (f"{header}\n"
                f"Status: {status_str}\n"
                f"Name Length: {self.name_len} Bytes\n"
                f"File Name: {file_name}\n"
                f"Data Size: {self.data_size} Bytes\n"
                f"Data Received:\n{data_received}\n")

# Creates a unique file name if a certain file already exists (instead of overriding)
def unique_file_name(file_name):
    #We check if the file name already exists in directory
    if os.path.exists(file_name):
        # We need to make a unique name, with (1)..(2)...whatever...incremented to it
        # We split the name to base name - extension
        base_name, ext = os.path.splitext(file_name)

        # We check for 1+ until we find a unique name
        i = 1
        unique_name = f"{base_name}({i}){ext}"
        while os.path.exists(unique_name):
            i += 1
            unique_name = f"{base_name}({i}){ext}"
        return unique_name
    return file_name