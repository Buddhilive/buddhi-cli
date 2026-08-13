(method_declaration
  receiver: (parameter_list (parameter_declaration type: (_) @receiver.type))
  name: (field_identifier) @name) @definition.method

(function_declaration
  name: (identifier) @name) @definition.function

(type_declaration
  (type_spec
    name: (type_identifier) @name
    type: (struct_type))) @definition.class

(import_spec
  path: (interpreted_string_literal) @import.path) @import

(call_expression
  function: (identifier) @call.name) @call

(call_expression
  function: (selector_expression
    operand: (identifier) @call.receiver
    field: (field_identifier) @call.name)) @call
