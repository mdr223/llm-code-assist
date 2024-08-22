// File: rustdb/src/storage/tuple.rs
use std::fmt;
// Define the RecordId struct
#[derive(Debug, Clone, PartialEq)]
pub struct RecordId {
    page_number: u32,
    position: u32,
}
// Define the Field enum
#[derive(Debug, Clone, PartialEq)]
pub enum Field {
    Integer(i32),
    String(String),
}
// Define the Tuple struct
#[derive(Debug, Clone, PartialEq)]
pub struct Tuple {
    record_id: Option<RecordId>,
    fields: Vec<Field>,
}
impl Tuple {
    // Constructor
    pub fn new(record_id: Option<RecordId>, fields: Vec<Field>) -> Self {
        Tuple { record_id, fields }
    }
    // Getter for record_id
    pub fn get_record_id(&self) -> Option<&RecordId> {
        self.record_id.as_ref()
    }
    // Getter for fields
    pub fn get_fields(&self) -> &Vec<Field> {
        &self.fields
    }
    // Setter for record_id
    pub fn set_record_id(&mut self, record_id: RecordId) {
        self.record_id = Some(record_id);
    }
    // Method to add a field
    pub fn add_field(&mut self, field: Field) {
        self.fields.push(field);
    }
    // Method to get a field by index
    pub fn get_field(&self, index: usize) -> Option<&Field> {
        self.fields.get(index)
    }
}
// Implement Display for Tuple
impl fmt::Display for Tuple {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Tuple(")?;
        if let Some(record_id) = &self.record_id {
            write!(f, "RecordId({}, {}), ", record_id.page_number, record_id.position)?;
        } else {
            write!(f, "No RecordId, ")?;
        }
        for (i, field) in self.fields.iter().enumerate() {
            if i > 0 {
                write!(f, ", ")?;
            }
            match field {
                Field::Integer(val) => write!(f, "{}", val)?,
                Field::String(val) => write!(f, "\"{}\"", val)?,
            }
        }
        write!(f, ")")
    }
}
// Implement Display for Field
impl fmt::Display for Field {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Field::Integer(val) => write!(f, "{}", val),
            Field::String(val) => write!(f, "\"{}\"", val),
        }
    }
}
