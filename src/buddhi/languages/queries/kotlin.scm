(class_declaration
  name: (identifier) @name) @definition.class

(function_declaration
  (user_type) @receiver.type
  name: (identifier) @name) @definition.function

(function_declaration
  name: (identifier) @name) @definition.function

(import
  (qualified_identifier) @import.path) @import

(call_expression
  (identifier) @call.name) @call

(call_expression
  (navigation_expression
    (identifier) @call.receiver
    (identifier) @call.name)) @call

(call_expression
  (navigation_expression
    (this_expression) @call.receiver
    (identifier) @call.name)) @call
