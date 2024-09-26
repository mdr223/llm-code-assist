import typing as t

class PageInterface:
    """
    Interface for a page.
    The page will have the following structure:
    Header:
    - 0-8 bytes: page number.
    - 8-16 bytes: page version.
    - 16-24 bytes: checksum.
    Content:
    - 24-page_size bytes: Arbitrary data.

    Note that the dirty flag, page latch, etc. are stored in memory as class variables, not written to disk.
    """
    from threading import Lock

    def __init__(self, page_num: int, data: bytes, create: bool = False):
        """
        Initializes the page with the given page number and data.
        If the page is being created, the header will be initialized.
        Otherwise, the header is assumed to be present in the data.

        Creates the page latch, dirty flag (set to false), etc. as necessary.
        """
        pass

    def set_bytes(self, offset: int, data: bytes) -> None:
        """
        Sets the bytes at the given offset.
        Will increment the version, set the dirty flag, but not update the checksum.
        The checksum will be updated when the page is about to be written to disk.
        """
        pass

    def get_bytes(self, offset: int, length: int) -> bytes:
        """
        Gets the bytes at the given offset.
        """
        pass

    def get_page_num(self) -> int:
        """
        Returns the page number.
        """
        pass

    def get_version(self) -> int:
        """
        Returns the page version.
        """
        pass

    def get_checksum(self) -> int:
        """
        Returns the checksum.
        """
        pass

    def get_page_size(self) -> int:
        """
        Returns the page size.
        """
        pass

    def is_dirty(self) -> bool:
        """
        Returns whether the page is dirty.
        """
        pass
    
    def get_latch(self) -> Lock:
        """
        Returns the page latch.
        """
        pass


    def get_for_write(self) -> bytes:
        """
        Returns the page data for writing.
        Recomputes the checksum if the page is dirty.
        Sets the page to clean, since it assumes the data is immediately flushed to disk.
        """
        pass


class Page(PageInterface):
    """
# Implementation Essentials
Should be straightforward to implement the Page class given the description.
    """
    pass
