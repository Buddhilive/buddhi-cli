from buddhi_ai.parser.entropy import calculate_entropy, filter_boilerplate

def test_entropy_high_information():
    code = "def complex_function(a, b):\n    return a * b + 12.3"
    score = calculate_entropy(code)
    assert score > 3.0, f"Expected >3.0, got {score}"

def test_entropy_boilerplate():
    code = "////////////////////////////////////////////////"
    score = calculate_entropy(code)
    assert score < 3.0, f"Expected <3.0, got {score}"

def test_filter_boilerplate():
    assert filter_boilerplate("////////////////////////////////////////////////", 3.0) is True
    assert filter_boilerplate("def complex_function(a, b):\n    return a * b + 12.3", 3.0) is False
