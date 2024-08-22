use std::collections::HashMap;
#[derive(Debug, Clone, PartialEq)]
pub enum FieldType {
    Integer,
    String,
    // Add more field types as needed
}
#[derive(Debug, Clone, PartialEq)]
pub enum Field {
    Integer(i32),
    String(String),
    // Add more field variants as needed
}
#[derive(Debug, Clone, PartialEq)]
pub struct Tuple {
    fields: HashMap<String, Field>,
    field_order: Vec<String>,
}
impl Tuple {
    pub fn new(fields: Vec<(&str, FieldType, Box<dyn std::any::Any>)>) -> Self {
        let mut tuple_fields = HashMap::new();
        let mut order = Vec::new();
        for (name, field_type, value) in fields {
            let field_value = match field_type {
                FieldType::Integer => {
                    Field::Integer(*value.downcast::<i32>().expect("Expected i32 value"))
                },
                FieldType::String => {
                    Field::String(*value.downcast::<String>().expect("Expected String value"))
                },
            };
            tuple_fields.insert(name.to_string(), field_value);
            order.push(name.to_string());
        }
        Tuple {
            fields: tuple_fields,
            field_order: order,
        }
    }
    pub fn field_count(&self) -> usize {
        self.fields.len()
    }
    pub fn get_field(&self, name: &str) -> Option<&Field> {
        self.fields.get(name)
    }
    pub fn set_field(&mut self, name: &str, value: Field) -> bool {
        if self.fields.contains_key(name) {
            self.fields.insert(name.to_string(), value);
            true
        } else {
            false
        }
    }
    pub fn field_names(&self) -> Vec<&str> {
        self.field_order.iter().map(|s| s.as_str()).collect()
    }
    pub fn field_types(&self) -> Vec<FieldType> {
        self.field_order
            .iter()
            .map(|name| match self.fields.get(name).unwrap() {
                Field::Integer(_) => FieldType::Integer,
                Field::String(_) => FieldType::String,
            })
            .collect()
    }
}
impl From<i32> for Field {
    fn from(value: i32) -> Self {
        Field::Integer(value)
    }
}
impl From<&str> for Field {
    fn from(value: &str) -> Self {
        Field::String(value.to_string())
    }
}
