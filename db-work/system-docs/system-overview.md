This system implements a database in Rust.

The database is implemented in the `rustdb/` directory.

MODULES
-----
The database currently has the following modules:
- **Storage Layer:** implemented in `rustdb/src/storage/` which contains the following files
  - `mod.rs`: the base interface for the storage layer; different access methods overwrite its core functionalities
  - `file_store.rs`: the access method which implements the storage layer in `mod.rs` using files on local disk
  - `tuple.rs`: a file containing the definition and implementation of tuples in the database system
