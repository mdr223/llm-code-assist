class ReplacementPolicyInterface:
    """
    Interface for a replacement policy.
    Used for unpinned pages.
    """
    def __init__(self):
        pass

    def add_unpinned(self, page_num: int) -> None:
        """
        Add the given page number to the eviction policy.
        """
        pass

    def evict(self) -> int:
        """
        Evict a page number with the lowest priority.
        """
        pass

    def remove(self, page_num: int) -> None:
        """
        Remove the given page number from the eviction policy.
        Called when an unpinned page is about to be pinned.
        """
        pass

    def contains(self, page_num: int) -> bool:
        """
        Returns whether the eviction policy contains the given page number.
        """
        pass


class LRU(ReplacementPolicyInterface):
    """
# Implementation Essentials
This is typical Least Recently Used (LRU) eviction policy.
Just use the classical list and a dictionary to implement this.
    """
    pass


