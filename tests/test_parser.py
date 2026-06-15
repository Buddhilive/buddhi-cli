from buddhi_ai.parser.tree_sitter import parse_file

def test_parse_file_python(tmp_path):
    # Create a temporary python file
    p = tmp_path / "sample.py"
    p.write_text("class MyClass:\n    def my_method(self):\n        pass\n\ndef my_func():\n    pass")
    
    nodes = parse_file(p)
    # We should see the class and the standalone function. 
    # my_method might be skipped because it's a child of the class, depending on the visitor logic,
    # or the class stops traversal to ignore children.
    types = [n["type"] for n in nodes]
    assert "class_definition" in types
    
    # Check that my_func is found (it is top-level)
    assert any(n["name"] == "my_func" for n in nodes)
