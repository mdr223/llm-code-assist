import typing as t
import threading


def assistant_codegen(description: str, *args, **kwargs):
    pass


class MetadataStoreInterface:
    """General interface for a disk-backed metadata store."""
    
    import typing as t
    PAGE_SIZE = 4096
    FIXED_KEY_SIZE = 8
    FIXED_VAL_SIZE = 8    
    def __init__(self, filename: str):
        """Initializes the metadata store with the given filename. Recover any data that was durably stored on disk."""
        pass

    def get(self, key: bytes) -> t.Optional[bytes]:
        """Returns the value associated with the given key, or None if the key is not present."""
        pass

    def set(self, key: bytes, value: bytes) -> None:
        """Sets the value associated with the given key."""
        pass

    def delete(self, key: bytes) -> None:
        """Deletes the given key."""
        pass

    def close(self) -> None:
        """Closes the metadata store."""
        pass

    def free_size(self) -> int:
        """Returns the free storage size of the metadata store."""
        pass


class MetadataStore(MetadataStoreInterface):
    _lock: threading.Lock
    _file: t.IO
    _map: t.Dict[bytes, bytes]
    _free_size: int


    def __init__(self, filename: str):
        self._lock = threading.Lock()
        self._map = {}
        self._free_size = self.PAGE_SIZE - 8  # Initial free size (excluding num_items)

        # Open the file in read-write binary mode
        self._file = assistant_codegen("Open file in read-write binary mode", filename)

        # Check if the file is initialized
        file_size = assistant_codegen("Get file size", self._file)
        if file_size < self.PAGE_SIZE:
            # Initialize the file with zeros
            assistant_codegen("Write zeros to fill the page", self._file, self.PAGE_SIZE)
        
        # Read the entire page from disk
        page_data = assistant_codegen("Read PAGE_SIZE bytes from the file", self._file)

        # Parse the number of items
        num_items = int.from_bytes(page_data[:8], byteorder='big')

        # Parse key-value pairs and populate the in-memory map
        offset = 8
        for _ in range(num_items):
            key = page_data[offset:offset + self.FIXED_KEY_SIZE]
            offset += self.FIXED_KEY_SIZE
            value = page_data[offset:offset + self.FIXED_VAL_SIZE]
            offset += self.FIXED_VAL_SIZE
            self._map[key] = value

        # Calculate free space
        self._free_size = self.PAGE_SIZE - (8 + num_items * (self.FIXED_KEY_SIZE + self.FIXED_VAL_SIZE))


    def _write_page(self) -> None:
        # Create a byte buffer of PAGE_SIZE
        buffer = bytearray(self.PAGE_SIZE)

        # Write the number of items to the buffer
        num_items = len(self._map)
        buffer[:8] = num_items.to_bytes(8, byteorder='big')

        # Iterate through the in-memory map, writing each key-value pair to the buffer
        offset = 8
        for key, value in self._map.items():
            buffer[offset:offset + self.FIXED_KEY_SIZE] = key
            offset += self.FIXED_KEY_SIZE
            buffer[offset:offset + self.FIXED_VAL_SIZE] = value
            offset += self.FIXED_VAL_SIZE

        # Pad the remaining space with zeros (already done by bytearray initialization)

        # Write the entire buffer to disk at offset 0
        assistant_codegen("Write buffer to file at offset 0", self._file, buffer)

        # Flush to ensure durability
        assistant_codegen("Flush file to ensure durability", self._file)


    def get(self, key: bytes) -> t.Optional[bytes]:
        with self._lock:
            return self._map.get(key)


    def set(self, key: bytes, value: bytes) -> None:
        if len(key) != self.FIXED_KEY_SIZE or len(value) != self.FIXED_VAL_SIZE:
            raise ValueError("Key and value must be of fixed size")

        with self._lock:
            # Check if there's enough free space
            required_space = self.FIXED_KEY_SIZE + self.FIXED_VAL_SIZE
            if key not in self._map:
                required_space += self.FIXED_KEY_SIZE + self.FIXED_VAL_SIZE

            if self._free_size < required_space:
                raise Exception("Not enough free space")

            # Update the in-memory map
            self._map[key] = value

            # Write the entire page to disk
            self._write_page()

            # Update the free space
            if key not in self._map:
                self._free_size -= required_space


    def delete(self, key: bytes) -> None:
        with self._lock:
            if key in self._map:
                del self._map[key]
                assistant_codegen("Call _write_page method to update disk state")
                self._free_size += self.FIXED_KEY_SIZE + self.FIXED_VAL_SIZE


    def close(self) -> None:
        with self._lock:
            # Flush any pending writes
            self._write_page()
            
            # Close the file
            assistant_codegen("Close the file", self._file)


    def free_size(self) -> int:
        with self._lock:
            return self._free_size

