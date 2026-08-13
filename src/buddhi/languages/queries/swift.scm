(class_declaration
  name: (type_identifier) @name) @definition.class

(class_declaration
  (user_type
    (type_identifier) @name)) @definition.extension

(protocol_declaration
  name: (type_identifier) @name) @definition.class

(function_declaration
  name: (simple_identifier) @name) @definition.function

(protocol_function_declaration
  name: (simple_identifier) @name) @definition.function

(import_declaration
  (identifier
    (simple_identifier) @import.path)) @import

(call_expression
  (simple_identifier) @call.name) @call

(call_expression
  (navigation_expression
    (self_expression) @call.receiver
    (navigation_suffix
      (simple_identifier) @call.name))) @call
