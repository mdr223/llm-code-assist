import typing as t

class ReplacementPolicyInterface:
    """
    Interface for a replacement policy.
    Used for unpinned pages.
    Can assume that it is not called concurrently.
    """
    def __init__(self):
        pass

    def add(self, page_num: int) -> None:
        """
        Add the given page number (64-bit integer) to the eviction policy.
        Called when a page is unpinned and becomes a candidate for eviction.
        Assumes the page is not already in the eviction policy.
        """
        pass

    def evict(self) -> t.Optional[int]:
        """
        Evict a page number with the lowest priority.
        Returns the evicted page number.
        """
        pass

    def remove(self, page_num: int) -> None:
        """
        Remove the given page number from the eviction policy.
        Called when an unpinned page is about to be pinned, and is no longer a candidate for eviction.
        """
        pass

    def is_empty(self) -> bool:
        """
        Returns whether the eviction policy is empty.
        """
        pass


class LRU(ReplacementPolicyInterface):
    """
# Implementation Essentials
This is typical Least Recently Used (LRU) eviction policy.
Just use the classical list and a dictionary to implement this.
    """
    pass



class RandomPolicy(ReplacementPolicyInterface):
    """
# Implementation Essentials
This is a random eviction policy.
It simply evicts a random page.
    """
    pass