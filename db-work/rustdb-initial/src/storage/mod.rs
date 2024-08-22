pub mod file_store;
pub mod tuple;
use tuple::Tuple;
use std::io::{Error as IoError, Result as IoResult};
pub struct Page;
pub trait HeapFile {
    fn read_page(&mut self, page_no: usize) -> IoResult<Page>;
    fn insert_tuple(&mut self, tuple: &Tuple) -> IoResult<()>;
    fn delete_tuple(&mut self, tuple: &Tuple) -> IoResult<()>;
    fn flush_page(&mut self, page: &Page) -> IoResult<()>;
    fn iterator(&self) -> Box<dyn Iterator<Item = IoResult<Tuple>>>;
}
pub struct HeapFileImpl;
impl HeapFile for HeapFileImpl {
    fn read_page(&mut self, _page_no: usize) -> IoResult<Page> {
        unimplemented!("Implemented by specific access methods")
    }
    fn insert_tuple(&mut self, _tuple: &Tuple) -> IoResult<()> {
        unimplemented!("Implemented by specific access methods")
    }
    fn delete_tuple(&mut self, _tuple: &Tuple) -> IoResult<()> {
        unimplemented!("Implemented by specific access methods")
    }
    fn flush_page(&mut self, _page: &Page) -> IoResult<()> {
        unimplemented!("Implemented by specific access methods")
    }
    fn iterator(&self) -> Box<dyn Iterator<Item = IoResult<Tuple>>> {
        unimplemented!("Implemented by specific access methods")
    }
}
