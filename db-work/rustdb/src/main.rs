mod storage;
use crate::storage::file_store::FileHeapFile;
use crate::storage::tuple::{Tuple, Field};
use crate::storage::HeapFile;

fn main() {
    // Create a new heap file
    let mut heap_file = FileHeapFile::new("test_heap_file.dat").expect("Failed to create heap file");

    // Create the first tuple
    let tuple1 = Tuple::new(None, vec![
        Field::Integer(42),
        Field::String("Hello, World!".to_string()),
    ]);

    // Create the second tuple
    let tuple2 = Tuple::new(None, vec![
        Field::Integer(100),
        Field::String("RustDB".to_string()),
    ]);

    // Insert the tuples into the heap file
    heap_file.insert_tuple(&tuple1).expect("Failed to insert tuple1");
    heap_file.insert_tuple(&tuple2).expect("Failed to insert tuple2");

    println!("Inserted two tuples into the heap file.");

    // Optional: Read back the tuples to verify insertion
    // This part would require implementing an iterator for the heap file
    // and is not included in the current implementation.
}
