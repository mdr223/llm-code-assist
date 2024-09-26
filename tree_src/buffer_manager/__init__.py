"""
I am implementing a buffer manager that manages pages in memory and on disk.

The buffer manager will have the following guarantees:
- Storage Space:
    * The buffer manager throws an error if it exceeds its capacity.
- Thread Safety and Consistency:
    * Multiple threads can read and write to the buffer manager concurrently.
    * Reads and writes to the same page should have a consistent sequential order.
- Durability:
    * The buffer manager will ensure that flushed data is durably stored on disk.
    * Likewise a page will not be evicted from memory until it is flushed to disk.
    * However, a page is not immediately writtent to disk when it is unpinned, unless flush is explicitly called.
- Atomicity:
    * Partial writes never occur.
"""
