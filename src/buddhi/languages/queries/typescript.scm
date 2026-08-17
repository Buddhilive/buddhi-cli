(class_declaration
  name: (type_identifier) @name) @definition.class

(interface_declaration
  name: (type_identifier) @name) @definition.class

(function_declaration
  name: (identifier) @name) @definition.function

(method_definition
  name: (property_identifier) @name) @definition.method

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
