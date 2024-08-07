The storage layer is implemented in `rustdb/src/storage/` and contains the following files:

`mod.rs`
-----
This file implements the base interface for all access methods. It contains a struct for a `HeapFile` which has abstract methods for:
- `readPage(pageNo)`: reading the specified page
- `insertTuple(tuple)`: inserting a tuple into the heap file
- `deleteTuple(tuple)`: deleting a tuple from the heap file
- `flushPage(page)`: flushing a page to the storage backend
- `iterator()`: iterator for reading all tuples in the heap file

`file_store.rs`
-----
This file implements the interface defined in `mod.rs` for the local disk access method. This file contains an implementation of the `HeapFile` struct -- and its abstract methods -- assuming a local disk storage backend.

`tuple.rs`
-----
This file contains the definition and implementation of tuples in the database system. It defines a `Tuple` struct which has:
- a record id (a tuple specifying the page number and position the tuple was read from)
- a list of fields
Each field in the `Tuple` may be an Integer or a String.