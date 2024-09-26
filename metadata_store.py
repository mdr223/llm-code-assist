
API_SPEC = """
This is a simple disk-backed metadata store capable of storing only a single page of key-value pairs.

Guarantees:
- Storage Space:
    * The store will simply block operations that would cause it to exceed its capacity.
- Thread Safety:
    * Multiple threads can read and write to the store concurrently.
    * Reads and writes to the key should have a consistent sequential order.
- Durabibility:
    * Once write operations return, the data will be durably stored on disk.
    * After restart, the store will recover the data that was durably stored on disk.
- Atomicity:
    * Partial writes never occur.

Operations:
- Shown in the `MetadataStoreInterface` interface.    
"""

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




OVERALL_IMPLEMENTATION_SPEC = """
We are going to implement the API above with the given guarantees.

The concrete class will be called `MetadataStore`; it will inherit from `MetadataStoreInterface`.

# Basic Structure
## In-Memory State
- Since the metadata is small, it will fully be cached in memory as a map.
    - Reads will only be done from memory.
    - Writes will update the disk, then update the memory.
- The free size and number of items will also be kept in memory and updated accordingly on writes.
- The metadata will be stored in the given file.

## Disk State
- The single page will be structured as <num_items><key1><value1><key2><value2>...<keyN><valueN>
- On recovery, the page will be fully read from disk, and the in-memory state (free size and map) will be updated.
- The page will be padded with zeros to ensure that the page size is always PAGE_SIZE.
- The file is open at all time to prevent frequent open/close operations.


## Initialization
- The file will be opened in read-write mode.
- On initialization, the page will be read from disk.
- If num_items (first 8 bytes) is not zero, the metadata will be recovered.
"""

FIRST_IMPLEMENTATION_SPEC = """
# First Implementation
Help me implement a first version.
It will be inefficient, but should be correct and fulfill the guarantees.

## Concurrency
Let's start with a global lock that will be acquired for the full duration of every operation.
- This will ensure that only one operation can be executed at a time.
- This will make the implementation thread-safe, but not concurrent.

## Consistency
- On every write, the page will be fully rewritten to disk.
- This saves us from having to locate the exact position of the key-value pair on disk.
    - We don't need to keep the data sorted.
"""


FIRST_IMPLEMENTATION_PLAN_EXAMPLE = """
# Example First Implementation Plan
## Initialization
This goes in the `__init__` function.
- Open the file in read-write mode.
    - Consider `uninitialized` if:
        - File size is less than PAGE_SIZE.
        - First 8 bytes are zero.
- If `uninitialized`, write zeros to the file to fill the page.
- Read the page from disk.
- Parse the number of items, then parse each key-value pair and insert into the in-memory map.

## Auxiliary Write Function
This is a helper function that writes the page to disk.
- Create a byte buffer.
- Write the number of items.
- Write each key-value pair.
- Pad the rest of the page with zeros.
- Write the buffer to disk.

## Get
- Acquire the lock.
- Read the value from the in-memory map.
- Release the lock.
- Return the value.

## Set
- Acquire the lock.
- Update the in-memory map.
- Call the auxiliary write function.
- Release the lock.

... and so on.
"""