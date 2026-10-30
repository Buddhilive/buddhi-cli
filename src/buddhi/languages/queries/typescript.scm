(class_declaration
  name: (type_identifier) @name
  (class_heritage [
    (extends_clause value: [(identifier) (member_expression)] @inherit.base)
    (implements_clause [(type_identifier) (generic_type)] @inherit.base)
  ])?
) @definition.class

(interface_declaration
  name: (type_identifier) @name
  (extends_type_clause (type_identifier) @inherit.base)?
) @definition.class

(function_declaration
  name: (identifier) @name) @definition.function

(method_definition
  name: (property_identifier) @name) @definition.method

(import_statement
  (import_clause (named_imports (import_specifier name: (identifier) @import.symbol)))?
  source: (string) @import.path
) @import

(import_statement
  source: (string) @import.path) @import

(call_expression
  function: (identifier) @call.name) @call

(call_expression
  function: (member_expression
    object: (identifier) @call.receiver
    property: (property_identifier) @call.name)) @call

(call_expression
  function: (member_expression
    object: (this) @call.receiver
    property: (property_identifier) @call.name)) @call
