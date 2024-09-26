
#include <cstdint>
#include <fstream>
#include <map>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <vector>

class MetadataStore {
public:
    static constexpr size_t PAGE_SIZE = 4096;
    static constexpr size_t FIXED_KEY_SIZE = 8;
    static constexpr size_t FIXED_VAL_SIZE = 8;

    MetadataStore(const std::string& filename) {
        _lock = std::make_unique<std::mutex>();
        _free_size = PAGE_SIZE - 8;  // Initial free size (excluding num_items)

        // Open the file in read-write binary mode
        _file.open(filename, std::ios::in | std::ios::out | std::ios::binary);
        if (!_file) {
            throw std::runtime_error("Failed to open file");
        }

        // Check if the file is initialized
        _file.seekg(0, std::ios::end);
        std::streampos file_size = _file.tellg();
        _file.seekg(0, std::ios::beg);

        if (file_size < PAGE_SIZE) {
            // Initialize the file with zeros
            std::vector<uint8_t> zeros(PAGE_SIZE, 0);
            _file.write(reinterpret_cast<char*>(zeros.data()), PAGE_SIZE);
            _file.flush();
        }

        // Read the entire page from disk
        std::vector<uint8_t> page_data(PAGE_SIZE);
        _file.read(reinterpret_cast<char*>(page_data.data()), PAGE_SIZE);

        // Parse the number of items
        uint64_t num_items = 0;
        for (int i = 0; i < 8; ++i) {
            num_items = (num_items << 8) | page_data[i];
        }

        // Parse key-value pairs and populate the in-memory map
        size_t offset = 8;
        for (uint64_t i = 0; i < num_items; ++i) {
            std::vector<uint8_t> key(page_data.begin() + offset, page_data.begin() + offset + FIXED_KEY_SIZE);
            offset += FIXED_KEY_SIZE;
            std::vector<uint8_t> value(page_data.begin() + offset, page_data.begin() + offset + FIXED_VAL_SIZE);
            offset += FIXED_VAL_SIZE;
            _map[key] = value;
        }

        // Calculate free space
        _free_size = PAGE_SIZE - (8 + num_items * (FIXED_KEY_SIZE + FIXED_VAL_SIZE));
    }

    std::optional<std::vector<uint8_t>> get(const std::vector<uint8_t>& key) {
        std::lock_guard<std::mutex> lock(*_lock);
        auto it = _map.find(key);
        if (it != _map.end()) {
            return it->second;
        }
        return std::nullopt;
    }

    void set(const std::vector<uint8_t>& key, const std::vector<uint8_t>& value) {
        if (key.size() != FIXED_KEY_SIZE || value.size() != FIXED_VAL_SIZE) {
            throw std::invalid_argument("Key and value must be of fixed size");
        }

        std::lock_guard<std::mutex> lock(*_lock);
        
        // Check if there's enough free space
        size_t required_space = 0;
        if (_map.find(key) == _map.end()) {
            required_space += FIXED_KEY_SIZE + FIXED_VAL_SIZE;
        }

        if (_free_size < required_space) {
            throw std::runtime_error("Not enough free space");
        }

        // Update the in-memory map
        _map[key] = value;

        // Write the entire page to disk
        _write_page();

        // Update the free space
        if (_map.find(key) == _map.end()) {
            _free_size -= required_space;
        }
    }

    void delete_key(const std::vector<uint8_t>& key) {
        std::lock_guard<std::mutex> lock(*_lock);
        auto it = _map.find(key);
        if (it != _map.end()) {
            _map.erase(it);
            _write_page();
            _free_size += FIXED_KEY_SIZE + FIXED_VAL_SIZE;
        }
    }

    void close() {
        std::lock_guard<std::mutex> lock(*_lock);
        _write_page();
        _file.close();
    }

    size_t free_size() {
        std::lock_guard<std::mutex> lock(*_lock);
        return _free_size;
    }

private:
    void _write_page() {
        // Create a byte buffer of PAGE_SIZE
        std::vector<uint8_t> buffer(PAGE_SIZE, 0);

        // Write the number of items to the buffer
        uint64_t num_items = _map.size();
        for (int i = 7; i >= 0; --i) {
            buffer[i] = num_items & 0xFF;
            num_items >>= 8;
        }

        // Iterate through the in-memory map, writing each key-value pair to the buffer
        size_t offset = 8;
        for (const auto& [key, value] : _map) {
            std::copy(key.begin(), key.end(), buffer.begin() + offset);
            offset += FIXED_KEY_SIZE;
            std::copy(value.begin(), value.end(), buffer.begin() + offset);
            offset += FIXED_VAL_SIZE;
        }

        // Write the entire buffer to disk at offset 0
        _file.seekp(0, std::ios::beg);
        _file.write(reinterpret_cast<char*>(buffer.data()), PAGE_SIZE);

        // Flush to ensure durability
        _file.flush();
    }

    std::unique_ptr<std::mutex> _lock;
    std::fstream _file;
    std::map<std::vector<uint8_t>, std::vector<uint8_t>> _map;
    size_t _free_size;
};
