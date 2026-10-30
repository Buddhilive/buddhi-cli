(class_declaration
  name: (identifier) @name
  (superclass (type_identifier) @inherit.base)?
  (super_interfaces (type_list (type_identifier) @inherit.base))?) @definition.class

(interface_declaration
  name: (identifier) @name
  (extends_interfaces (type_list (type_identifier) @inherit.base))?) @definition.class

(method_declaration
  name: (identifier) @name) @definition.method

(import_declaration
  (scoped_identifier) @import.path) @import

(method_invocation
  name: (identifier) @call.name) @call

(method_invocation
  object: (identifier) @call.receiver
  name: (identifier) @call.name) @call

(method_invocation
  object: (this) @call.receiver
  name: (identifier) @call.name) @call
