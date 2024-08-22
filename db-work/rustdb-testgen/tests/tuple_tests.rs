#[cfg(test)]
mod tests {
    use rustdb_testgen::{Tuple, Field, FieldType};

    #[test]
    fn test_tuple_creation() {
        let tuple = Tuple::new(vec![
            ("id", FieldType::Integer, Box::new(1)),
            ("name", FieldType::String, Box::new(String::from("Alice"))),
            ("age", FieldType::Integer, Box::new(30)),
        ]);

        assert_eq!(tuple.field_count(), 3);
    }

    #[test]
    fn test_tuple_get_field() {
        let tuple = Tuple::new(vec![
            ("id", FieldType::Integer, Box::new(1)),
            ("name", FieldType::String, Box::new(String::from("Bob"))),
            ("age", FieldType::Integer, Box::new(25)),
        ]);

        assert_eq!(tuple.get_field("id"), Some(&Field::Integer(1)));
        assert_eq!(tuple.get_field("name"), Some(&Field::String("Bob".to_string())));
        assert_eq!(tuple.get_field("age"), Some(&Field::Integer(25)));
        assert_eq!(tuple.get_field("non_existent"), None);
    }

    #[test]
    fn test_tuple_set_field() {
        let mut tuple = Tuple::new(vec![
            ("id", FieldType::Integer, Box::new(1)),
            ("name", FieldType::String, Box::new(String::from("Charlie"))),
            ("age", FieldType::Integer, Box::new(35)),
        ]);

        assert!(tuple.set_field("age", Field::Integer(36)));
        assert_eq!(tuple.get_field("age"), Some(&Field::Integer(36)));

        assert!(tuple.set_field("name", Field::String("Charles".to_string())));
        assert_eq!(tuple.get_field("name"), Some(&Field::String("Charles".to_string())));

        assert!(!tuple.set_field("non_existent", Field::Integer(0)));
    }

    #[test]
    fn test_tuple_field_names() {
        let tuple = Tuple::new(vec![
            ("id", FieldType::Integer, Box::new(1)),
            ("name", FieldType::String, Box::new(String::from("David"))),
            ("age", FieldType::Integer, Box::new(40)),
        ]);

        let field_names = tuple.field_names();
        assert_eq!(field_names, vec!["id", "name", "age"]);
    }

    #[test]
    fn test_tuple_field_types() {
        let tuple = Tuple::new(vec![
            ("id", FieldType::Integer, Box::new(1)),
            ("name", FieldType::String, Box::new(String::from("Eve"))),
            ("age", FieldType::Integer, Box::new(28)),
        ]);

        let field_types = tuple.field_types();
        assert_eq!(field_types, vec![FieldType::Integer, FieldType::String, FieldType::Integer]);
    }

    #[test]
    fn test_tuple_equality() {
        let tuple1 = Tuple::new(vec![
            ("id", FieldType::Integer, Box::new(1)),
            ("name", FieldType::String, Box::new(String::from("Frank"))),
            ("age", FieldType::Integer, Box::new(45)),
        ]);

        let tuple2 = Tuple::new(vec![
            ("id", FieldType::Integer, Box::new(1)),
            ("name", FieldType::String, Box::new(String::from("Frank"))),
            ("age", FieldType::Integer, Box::new(45)),
        ]);

        let tuple3 = Tuple::new(vec![
            ("id", FieldType::Integer, Box::new(2)),
            ("name", FieldType::String, Box::new(String::from("Grace"))),
            ("age", FieldType::Integer, Box::new(32)),
        ]);

        assert_eq!(tuple1, tuple2);
        assert_ne!(tuple1, tuple3);
    }
}
