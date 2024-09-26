
use std::collections::HashMap;
use std::fs::{File, OpenOptions};
use std::io::{Read, Write, Seek, SeekFrom};
use std::sync::Mutex;
use byteorder::{BigEndian, ReadBytesExt, WriteBytesExt};

const PAGE_SIZE: usize = 4096;
const FIXED_KEY_SIZE: usize = 8;
const FIXED_VAL_SIZE: usize = 8;

// Define the MetadataStoreInterface trait
pub trait MetadataStoreInterface {
    fn get(&self, key: &[u8]) -> Option<Vec<u8>>;
    fn set(&self, key: &[u8], value: &[u8]) -> Result<(), String>;
    fn delete(&self, key: &[u8]) -> Result<(), String>;
    fn close(&self) -> Result<(), String>;
    fn free_size(&self) -> usize;
}

pub struct MetadataStore {
    file: Mutex<File>,
    map: Mutex<HashMap<Vec<u8>, Vec<u8>>>,
    free_size: Mutex<usize>,
}

impl MetadataStore {
    pub fn new(filename: &str) -> Result<Self, String> {
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .open(filename)
            .map_err(|e| format!("Failed to open file: {}", e))?;

        let mut store = MetadataStore {
            file: Mutex::new(file),
            map: Mutex::new(HashMap::new()),
            free_size: Mutex::new(PAGE_SIZE - 8), // Initial free size (excluding num_items)
        };

        store.initialize()?;
        Ok(store)
    }

    fn initialize(&mut self) -> Result<(), String> {
        let mut file = self.file.lock().unwrap();
        let file_size = file.metadata().map_err(|e| format!("Failed to get file metadata: {}", e))?.len();

        if file_size < PAGE_SIZE as u64 {
            // Initialize the file with zeros
            file.set_len(PAGE_SIZE as u64).map_err(|e| format!("Failed to set file length: {}", e))?;
            file.seek(SeekFrom::Start(0)).map_err(|e| format!("Failed to seek: {}", e))?;
            file.write_all(&vec![0; PAGE_SIZE]).map_err(|e| format!("Failed to write zeros: {}", e))?;
        }

        // Read the entire page from disk
        let mut page_data = vec![0; PAGE_SIZE];
        file.seek(SeekFrom::Start(0)).map_err(|e| format!("Failed to seek: {}", e))?;
        file.read_exact(&mut page_data).map_err(|e| format!("Failed to read page: {}", e))?;

        // Parse the number of items
        let num_items = (&page_data[0..8]).read_u64::<BigEndian>().map_err(|e| format!("Failed to read num_items: {}", e))?;

        // Parse key-value pairs and populate the in-memory map
        let mut map = self.map.lock().unwrap();
        let mut offset = 8;
        for _ in 0..num_items {
            let key = page_data[offset..offset + FIXED_KEY_SIZE].to_vec();
            offset += FIXED_KEY_SIZE;
            let value = page_data[offset..offset + FIXED_VAL_SIZE].to_vec();
            offset += FIXED_VAL_SIZE;
            map.insert(key, value);
        }

        // Calculate free space
        let used_space = 8 + (num_items as usize) * (FIXED_KEY_SIZE + FIXED_VAL_SIZE);
        *self.free_size.lock().unwrap() = PAGE_SIZE - used_space;

        Ok(())
    }

    fn write_page(&self) -> Result<(), String> {
        let mut buffer = vec![0; PAGE_SIZE];
        let map = self.map.lock().unwrap();

        // Write the number of items to the buffer
        (&mut buffer[0..8]).write_u64::<BigEndian>(map.len() as u64)
            .map_err(|e| format!("Failed to write num_items: {}", e))?;

        // Iterate through the in-memory map, writing each key-value pair to the buffer
        let mut offset = 8;
        for (key, value) in map.iter() {
            buffer[offset..offset + FIXED_KEY_SIZE].copy_from_slice(key);
            offset += FIXED_KEY_SIZE;
            buffer[offset..offset + FIXED_VAL_SIZE].copy_from_slice(value);
            offset += FIXED_VAL_SIZE;
        }

        // Write the entire buffer to disk at offset 0
        let mut file = self.file.lock().unwrap();
        file.seek(SeekFrom::Start(0)).map_err(|e| format!("Failed to seek: {}", e))?;
        file.write_all(&buffer).map_err(|e| format!("Failed to write page: {}", e))?;
        file.flush().map_err(|e| format!("Failed to flush: {}", e))?;

        Ok(())
    }
}

impl MetadataStoreInterface for MetadataStore {
    fn get(&self, key: &[u8]) -> Option<Vec<u8>> {
        let map = self.map.lock().unwrap();
        map.get(key).cloned()
    }

    fn set(&self, key: &[u8], value: &[u8]) -> Result<(), String> {
        if key.len() != FIXED_KEY_SIZE || value.len() != FIXED_VAL_SIZE {
            return Err("Key and value must be of fixed size".to_string());
        }

        let mut map = self.map.lock().unwrap();
        let mut free_size = self.free_size.lock().unwrap();

        // Check if there's enough free space
        let required_space = if !map.contains_key(key) {
            FIXED_KEY_SIZE + FIXED_VAL_SIZE
        } else {
            0
        };

        if *free_size < required_space {
            return Err("Not enough free space".to_string());
        }

        // Update the in-memory map
        map.insert(key.to_vec(), value.to_vec());

        // Write the entire page to disk
        drop(map); // Release the lock before calling write_page
        self.write_page()?;

        // Update the free space
        *free_size -= required_space;

        Ok(())
    }

    fn delete(&self, key: &[u8]) -> Result<(), String> {
        let mut map = self.map.lock().unwrap();
        let mut free_size = self.free_size.lock().unwrap();

        if map.remove(key).is_some() {
            drop(map); // Release the lock before calling write_page
            self.write_page()?;
            *free_size += FIXED_KEY_SIZE + FIXED_VAL_SIZE;
        }

        Ok(())
    }

    fn close(&self) -> Result<(), String> {
        // Flush any pending writes
        self.write_page()?;
        
        // The file will be automatically closed when the MetadataStore is dropped
        Ok(())
    }

    fn free_size(&self) -> usize {
        *self.free_size.lock().unwrap()
    }
}

// Implement Drop trait to ensure the file is properly closed
impl Drop for MetadataStore {
    fn drop(&mut self) {
        // The file will be automatically closed when the Mutex<File> is dropped
    }
}
