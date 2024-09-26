"""
The buffer manager safely caches pages between storage layers.
It is fully thread-safe and provides strong guarantees for durability and atomicity.
"""

import typing as t

from .page import PageInterface
from .replacement_policy import ReplacementPolicyInterface

class BufferManagerInterface:
    """Interface for buffer manager."""
    def __init__(self, filename: str, page_size: int, max_size_bytes: int, replacement_policy: ReplacementPolicyInterface):
        """
        Initializes the buffer manager with the given filename, page size, and maximum size in bytes.
        For an existing file, the page_size must match the existing page size.
        """
        pass

    def pin(self, page_num: int) -> t.Optional[PageInterface]:
        """
        Pin the page with the given page number. Returns the page if it is in the buffer, None otherwise.
        If the buffer manager is full, a page will be evicted from the replacement policy.
            - If the evicted page is dirty, it will be written to disk.
        """
        pass

    def unpin(self, page: PageInterface) -> None:
        """Unpin the given page."""
        pass

    def flush(self, page_num: int) -> None:
        """
        Flush the given page to disk.
        Noop if the page isn't in the buffer manager or if the page is not dirty.
        """
        pass

    def create_page(self, page_num: int) -> PageInterface:
        """
        Create a new page with the given page number.
        The returned page will be pinned.
        Caller is responsible for making sure the new page does not overwrite an existing page.
        """
        pass

    def delete_page(self, page: PageInterface) -> None:
        """
        Delete the page with the given page number.
        Caller must be the only one with the page pinned.
        """
        pass


class BufferManager(BufferManagerInterface):
    """
# Implementation Essentials

## In-Memory State
- A page table map from page number to page.
- A pinned map from page number to number of pins.
- The unpinned set is tracked by the replacement policy.


## Disk State
- Pages are stored in the given file, at the offset page_num * page_size.
- Assume the page_size is small-enough for atomic writes to disk.
- The file is opened in binary RW mode.
- Dirty pages are written back when:
    (1) Evicted from a full buffer manager.
    (2) Explicitly flushed to disk.

## Operations
- Pinning a page:
    - If a page is already in memory, increment the pin count and return the page.
    - If a page is not in memory, read it from disk, add it to the page table and pinned map, and return the page.
    - If the buffer manager is full, evict a page using the replacement policy.
- Unpinning a page:
    - Decrement the pin count.
    - Erase the page from the pinned map if the pin count is zero, and move the item to the replacement policy.
- Eviction and Flushing a page:
    - Just write the page to disk if it is dirty.
    - Be sure to update the file size if the page number is out of bounds.
- Creating a page:
    - Just create the page in memory and pin it.
    - No need to write to disk immediately.    
    """
    pass

