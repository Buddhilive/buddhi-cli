(struct_item
  name: (type_identifier) @name) @definition.class

(impl_item
  type: (type_identifier) @name) @definition.impl

(function_item
  name: (identifier) @name) @definition.function

(use_declaration
  argument: (_) @import.path) @import

(call_expression
  function: (identifier) @call.name) @call

(call_expression
  function: (field_expression
    value: (identifier) @call.receiver
    field: (field_identifier) @call.name)) @call

(call_expression
  function: (field_expression
    value: (self) @call.receiver
    field: (field_identifier) @call.name)) @call
