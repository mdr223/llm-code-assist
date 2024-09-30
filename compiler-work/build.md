### STEP 1.1
#### Test: None
#### References: None
Create the unit tests for a struct defining a `Tuple` (i.e. a record), which is a collection of `Field`s. `Field` should get its own struct as well, and it can accept a `field_name` string and a `field_value` which is an integer or string. The unit tests should test:
- `Field` constructor works and can accept strings, ints, and field names
- `Tuple` constructor works and can accept various different fields
    - constructor should throw an exception if duplicate field names are provided
- `Tuple` equality works and checks all `Field` names and values for an exact match
- `Tuple` has a method to retrieve its type, which is a sorted list of `Field` names

### STEP 1.2
#### Test: None
#### References: 1.1
Create a class defining a `tuple` (i.e. a record), which is a collection of `field`s, each of which has a type and a value. Tuples have types which are uniquely defined by the field names and types.
