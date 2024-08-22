package storage

// FieldType represents the type of a field in a tuple
type FieldType int

const (
	FieldTypeInteger FieldType = iota
	FieldTypeString
)

// Field represents a single field in a tuple
type Field struct {
	Name  string
	Type  FieldType
	Value interface{}
}

// Tuple represents a collection of fields
type Tuple struct {
	fields []Field
}

// NewTuple creates a new Tuple with the given fields
func NewTuple(fields []Field) *Tuple {
	return &Tuple{fields: fields}
}

// FieldCount returns the number of fields in the tuple
func (t *Tuple) FieldCount() int {
	return len(t.fields)
}

// GetField returns the field with the given name
func (t *Tuple) GetField(name string) (Field, bool) {
	for _, field := range t.fields {
		if field.Name == name {
			return field, true
		}
	}
	return Field{}, false
}

// SetField sets the value of the field with the given name
func (t *Tuple) SetField(name string, value interface{}) bool {
	for i, field := range t.fields {
		if field.Name == name {
			t.fields[i].Value = value
			return true
		}
	}
	return false
}

// FieldNames returns a slice of all field names in the tuple
func (t *Tuple) FieldNames() []string {
	names := make([]string, len(t.fields))
	for i, field := range t.fields {
		names[i] = field.Name
	}
	return names
}

// FieldTypes returns a slice of all field types in the tuple
func (t *Tuple) FieldTypes() []FieldType {
	types := make([]FieldType, len(t.fields))
	for i, field := range t.fields {
		types[i] = field.Type
	}
	return types
}

// Equals checks if two tuples are equal
func (t *Tuple) Equals(other *Tuple) bool {
	if len(t.fields) != len(other.fields) {
		return false
	}
	for i, field := range t.fields {
		if field.Name != other.fields[i].Name ||
			field.Type != other.fields[i].Type ||
			field.Value != other.fields[i].Value {
			return false
		}
	}
	return true
}
