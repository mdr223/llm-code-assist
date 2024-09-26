CREATE TABLE IF NOT EXISTS type_lists (
    sys_name TEXT PRIMARY KEY,
    types JSON NOT NULL,
    confirmed BOOLEAN NOT NULL DEFAULT 0
);


CREATE TABLE IF NOT EXISTS type_docs (
    sys_name TEXT,
    type_name TEXT,
    doc TEXT NOT NULL,
    summary JSON NOT NULL,
    confirmed BOOLEAN NOT NULL DEFAULT 0,
    PRIMARY KEY (sys_name, type_name)
);

CREATE TABLE IF NOT EXISTS type_value_gens (
    sys_name TEXT,
    type_name TEXT,
    value_gen_code TEXT NOT NULL,
    code_output_examples JSON NOT NULL,
    confirmed BOOLEAN NOT NULL DEFAULT 0,
    PRIMARY KEY (sys_name, type_name)
);

CREATE TABLE IF NOT EXISTS function_categories (
    sys_name TEXT PRIMARY KEY,
    categories JSON NOT NULL,
    confirmed BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS functions_by_category (
    sys_name TEXT,
    category TEXT,
    functions JSON NOT NULL,
    confirmed BOOLEAN NOT NULL DEFAULT 0,
    PRIMARY KEY (sys_name, category)
);

CREATE TABLE IF NOT EXISTS function_documentations (
    sys_name TEXT,
    category TEXT,
    fn_name TEXT,
    documentation TEXT NOT NULL,
    confirmed BOOLEAN NOT NULL DEFAULT 0,
    PRIMARY KEY (sys_name, category, fn_name)
);
