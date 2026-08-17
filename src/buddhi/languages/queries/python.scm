(class_definition
  name: (identifier) @name) @definition.class

(function_definition
  name: (identifier) @name) @definition.function

(import_statement
  name: (dotted_name) @import.path) @import

(import_statement
  name: (aliased_import
    name: (dotted_name) @import.path)) @import

(import_from_statement
  module_name: (dotted_name) @import.path) @import

(import_from_statement
  module_name: (relative_import) @import.path) @import

(call
  function: (identifier) @call.name) @call

(call
  function: (attribute
    object: (identifier) @call.receiver
    attribute: (identifier) @call.name)) @call
