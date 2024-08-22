This system implements a project in Go.

The project is implemented in the `godb-testgen/` directory.

MODULES
-----
**Storage Manager:** the storage manager manages the database's data in ephemeral and persistent storage. It contains abstractions for tuples, heap pages, heap files, and a buffer pool.