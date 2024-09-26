package metadatastore

import (
	"encoding/binary"
	"errors"
	"os"
	"sync"
)

const (
	PageSize     = 4096
	FixedKeySize = 8
	FixedValSize = 8
)

// MetadataStore represents a disk-backed metadata store
type MetadataStore struct {
	lock     sync.Mutex
	file     *os.File
	data     map[string][]byte
	freeSize int64
}

// NewMetadataStore initializes a new MetadataStore with the given filename
func NewMetadataStore(filename string) (*MetadataStore, error) {
	ms := &MetadataStore{
		data:     make(map[string][]byte),
		freeSize: PageSize - 8, // Initial free size (excluding num_items)
	}

	// Open the file in read-write mode
	file, err := os.OpenFile(filename, os.O_RDWR|os.O_CREATE, 0666)
	if err != nil {
		return nil, err
	}
	ms.file = file

	// Check if the file is initialized
	fileInfo, err := file.Stat()
	if err != nil {
		return nil, err
	}

	if fileInfo.Size() < PageSize {
		// Initialize the file with zeros
		if err := ms.writeZeros(); err != nil {
			return nil, err
		}
	}

	// Read the entire page from disk
	pageData := make([]byte, PageSize)
	if _, err := file.ReadAt(pageData, 0); err != nil {
		return nil, err
	}

	// Parse the number of items
	numItems := binary.BigEndian.Uint64(pageData[:8])

	// Parse key-value pairs and populate the in-memory map
	offset := int64(8)
	for i := uint64(0); i < numItems; i++ {
		key := string(pageData[offset : offset+FixedKeySize])
		offset += FixedKeySize
		value := pageData[offset : offset+FixedValSize]
		offset += FixedValSize
		ms.data[key] = value
	}

	// Calculate free space
	ms.freeSize = PageSize - (8 + int64(numItems)*(FixedKeySize+FixedValSize))

	return ms, nil
}

// writeZeros initializes the file with zeros
func (ms *MetadataStore) writeZeros() error {
	zeros := make([]byte, PageSize)
	_, err := ms.file.WriteAt(zeros, 0)
	return err
}

// writePage writes the entire page to disk
func (ms *MetadataStore) writePage() error {
	buffer := make([]byte, PageSize)

	// Write the number of items to the buffer
	binary.BigEndian.PutUint64(buffer[:8], uint64(len(ms.data)))

	// Iterate through the in-memory map, writing each key-value pair to the buffer
	offset := 8
	for key, value := range ms.data {
		copy(buffer[offset:offset+FixedKeySize], []byte(key))
		offset += FixedKeySize
		copy(buffer[offset:offset+FixedValSize], value)
		offset += FixedValSize
	}

	// Write the entire buffer to disk at offset 0
	if _, err := ms.file.WriteAt(buffer, 0); err != nil {
		return err
	}

	// Flush to ensure durability
	return ms.file.Sync()
}

// Get retrieves a value for a given key
func (ms *MetadataStore) Get(key []byte) ([]byte, bool) {
	ms.lock.Lock()
	defer ms.lock.Unlock()

	value, ok := ms.data[string(key)]
	return value, ok
}

// Set sets a value for a given key
func (ms *MetadataStore) Set(key, value []byte) error {
	if len(key) != FixedKeySize || len(value) != FixedValSize {
		return errors.New("key and value must be of fixed size")
	}

	ms.lock.Lock()
	defer ms.lock.Unlock()

	// Check if there's enough free space
	requiredSpace := int64(0)
	if _, exists := ms.data[string(key)]; !exists {
		requiredSpace += FixedKeySize + FixedValSize
	}

	if ms.freeSize < requiredSpace {
		return errors.New("not enough free space")
	}

	// Update the in-memory map
	ms.data[string(key)] = value

	// Write the entire page to disk
	if err := ms.writePage(); err != nil {
		return err
	}

	// Update the free space
	if requiredSpace > 0 {
		ms.freeSize -= requiredSpace
	}

	return nil
}

// Delete deletes a key-value pair
func (ms *MetadataStore) Delete(key []byte) error {
	ms.lock.Lock()
	defer ms.lock.Unlock()

	if _, exists := ms.data[string(key)]; exists {
		delete(ms.data, string(key))
		if err := ms.writePage(); err != nil {
			return err
		}
		ms.freeSize += FixedKeySize + FixedValSize
	}

	return nil
}

// Close closes the metadata store
func (ms *MetadataStore) Close() error {
	ms.lock.Lock()
	defer ms.lock.Unlock()

	// Flush any pending writes
	if err := ms.writePage(); err != nil {
		return err
	}

	// Close the file
	return ms.file.Close()
}

// FreeSize returns the free storage size
func (ms *MetadataStore) FreeSize() int64 {
	ms.lock.Lock()
	defer ms.lock.Unlock()

	return ms.freeSize
}
