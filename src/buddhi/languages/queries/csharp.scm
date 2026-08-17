(class_declaration
  name: (identifier) @name) @definition.class

(method_declaration
  name: (identifier) @name) @definition.method

(using_directive
  (identifier) @import.path) @import

(using_directive
  (qualified_name) @import.path) @import

(invocation_expression
  function: (identifier) @call.name) @call

(invocation_expression
  function: (member_access_expression
    expression: (identifier) @call.receiver
    name: (identifier) @call.name)) @call

(invocation_expression
  function: (member_access_expression
    expression: "this" @call.receiver
    name: (identifier) @call.name)) @call
