import pytest

from buddhi.graph.extractor import extract_file
from buddhi.languages.registry import available_languages, get_spec

_UNAVAILABLE = {lang for lang, err in available_languages().items() if err is not None}

SAMPLES: dict[str, bytes] = {
    "python": b"""
class Foo:
    def bar(self):
        helper()

def helper():
    pass
""",
    "javascript": b"""
class Widget {
  render() {
    helper();
  }
}
function helper() {}
""",
    "typescript": b"""
class Widget {
  render(): void {
    helper();
  }
}
function helper(): void {}
""",
    "go": b"""
package main
type Widget struct { Name string }
func (w *Widget) Render() {
	helper()
}
func helper() {}
""",
    "rust": b"""
struct Widget { name: String }
impl Widget {
    fn render(&self) {
        helper();
    }
}
fn helper() {}
""",
    "csharp": b"""
class Widget {
  void Render() {
    Helper();
  }
}
""",
    "java": b"""
class Widget {
  void render() {
    helper();
  }
}
""",
    "kotlin": b"""
class Widget {
    fun render() {
        helper()
    }
}
fun helper() {}
""",
    "swift": b"""
class Widget {
    func render() {
        helper()
    }
}
func helper() {}
""",
}

EXPECTED_DEFINITION_NAMES: dict[str, set[str]] = {
    "python": {"Foo", "bar", "helper"},
    "javascript": {"Widget", "render", "helper"},
    "typescript": {"Widget", "render", "helper"},
    "go": {"Widget", "Render", "helper"},
    "rust": {"Widget", "render", "helper"},
    "csharp": {"Widget", "Render"},
    "java": {"Widget", "render"},
    "kotlin": {"Widget", "render", "helper"},
    "swift": {"Widget", "render", "helper"},
}


@pytest.mark.parametrize("language", sorted(SAMPLES))
def test_extract_definitions_for_language(language: str) -> None:
    if language in _UNAVAILABLE:
        pytest.skip(f"grammar unavailable for {language}")

    spec = get_spec(language)
    assert spec is not None

    extracted = extract_file(SAMPLES[language], spec)

    names = {d.local_name for d in extracted.definitions}
    assert EXPECTED_DEFINITION_NAMES[language] <= names
    assert not extracted.parse_had_errors


def test_go_method_receiver_captured() -> None:
    spec = get_spec("go")
    assert spec is not None
    extracted = extract_file(SAMPLES["go"], spec)
    method = next(d for d in extracted.definitions if d.local_name == "Render")
    assert method.receiver_type == "Widget"


def test_rust_impl_becomes_class_like_container() -> None:
    spec = get_spec("rust")
    assert spec is not None
    extracted = extract_file(SAMPLES["rust"], spec)
    kinds = {d.local_name: d.kind for d in extracted.definitions}
    assert kinds["Widget"] == "class"  # the impl block itself


def test_kotlin_extension_function_receiver() -> None:
    spec = get_spec("kotlin")
    assert spec is not None
    extracted = extract_file(b"fun Widget.extra() {}", spec)
    defn = next(d for d in extracted.definitions if d.local_name == "extra")
    assert defn.receiver_type == "Widget"


def test_swift_extension_reuses_extended_type_name() -> None:
    spec = get_spec("swift")
    assert spec is not None
    extracted = extract_file(b"extension Widget { func extra() {} }", spec)
    names = {d.local_name for d in extracted.definitions}
    assert "Widget" in names
    assert "extra" in names
