package storage

import (
	"testing"
	"reflect"
)

func TestTupleCreation(t *testing.T) {
	tuple := NewTuple([]Field{
		{Name: "id", Type: FieldTypeInteger, Value: 1},
		{Name: "name", Type: FieldTypeString, Value: "Alice"},
		{Name: "age", Type: FieldTypeInteger, Value: 30},
	})

	if tuple.FieldCount() != 3 {
		t.Errorf("Expected field count of 3, got %d", tuple.FieldCount())
	}
}

func TestTupleGetField(t *testing.T) {
	tuple := NewTuple([]Field{
		{Name: "id", Type: FieldTypeInteger, Value: 1},
		{Name: "name", Type: FieldTypeString, Value: "Bob"},
		{Name: "age", Type: FieldTypeInteger, Value: 25},
	})

	tests := []struct {
		name     string
		expected interface{}
	}{
		{"id", 1},
		{"name", "Bob"},
		{"age", 25},
	}

	for _, tt := range tests {
		field, ok := tuple.GetField(tt.name)
		if !ok {
			t.Errorf("Failed to get field %s", tt.name)
		}
		if field.Value != tt.expected {
			t.Errorf("For field %s, expected %v, got %v", tt.name, tt.expected, field.Value)
		}
	}

	_, ok := tuple.GetField("non_existent")
	if ok {
		t.Error("GetField should return false for non-existent field")
	}
}

func TestTupleSetField(t *testing.T) {
	tuple := NewTuple([]Field{
		{Name: "id", Type: FieldTypeInteger, Value: 1},
		{Name: "name", Type: FieldTypeString, Value: "Charlie"},
		{Name: "age", Type: FieldTypeInteger, Value: 35},
	})

	if !tuple.SetField("age", 36) {
		t.Error("Failed to set existing field")
	}
	if field, ok := tuple.GetField("age"); !ok || field.Value != 36 {
		t.Errorf("Expected age to be 36, got %v", field.Value)
	}

	if !tuple.SetField("name", "Charles") {
		t.Error("Failed to set existing field")
	}
	if field, ok := tuple.GetField("name"); !ok || field.Value != "Charles" {
		t.Errorf("Expected name to be Charles, got %v", field.Value)
	}

	if tuple.SetField("non_existent", 0) {
		t.Error("SetField should return false for non-existent field")
	}
}

func TestTupleFieldNames(t *testing.T) {
	tuple := NewTuple([]Field{
		{Name: "id", Type: FieldTypeInteger, Value: 1},
		{Name: "name", Type: FieldTypeString, Value: "David"},
		{Name: "age", Type: FieldTypeInteger, Value: 40},
	})

	expectedNames := []string{"id", "name", "age"}
	names := tuple.FieldNames()

	if !reflect.DeepEqual(names, expectedNames) {
		t.Errorf("Expected field names %v, got %v", expectedNames, names)
	}
}

func TestTupleFieldTypes(t *testing.T) {
	tuple := NewTuple([]Field{
		{Name: "id", Type: FieldTypeInteger, Value: 1},
		{Name: "name", Type: FieldTypeString, Value: "Eve"},
		{Name: "age", Type: FieldTypeInteger, Value: 28},
	})

	expectedTypes := []FieldType{FieldTypeInteger, FieldTypeString, FieldTypeInteger}
	types := tuple.FieldTypes()

	if !reflect.DeepEqual(types, expectedTypes) {
		t.Errorf("Expected field types %v, got %v", expectedTypes, types)
	}
}

func TestTupleEquality(t *testing.T) {
	tuple1 := NewTuple([]Field{
		{Name: "id", Type: FieldTypeInteger, Value: 1},
		{Name: "name", Type: FieldTypeString, Value: "Frank"},
		{Name: "age", Type: FieldTypeInteger, Value: 45},
	})

	tuple2 := NewTuple([]Field{
		{Name: "id", Type: FieldTypeInteger, Value: 1},
		{Name: "name", Type: FieldTypeString, Value: "Frank"},
		{Name: "age", Type: FieldTypeInteger, Value: 45},
	})

	tuple3 := NewTuple([]Field{
		{Name: "id", Type: FieldTypeInteger, Value: 2},
		{Name: "name", Type: FieldTypeString, Value: "Grace"},
		{Name: "age", Type: FieldTypeInteger, Value: 32},
	})

	if !tuple1.Equals(tuple2) {
		t.Error("tuple1 and tuple2 should be equal")
	}

	if tuple1.Equals(tuple3) {
		t.Error("tuple1 and tuple3 should not be equal")
	}
}

