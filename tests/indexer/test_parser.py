from anneal.indexer.parser import parse_file, detect_language, Definition, Import


def test_detect_python():
    assert detect_language("foo.py") == "python"

def test_detect_javascript():
    assert detect_language("foo.js") == "javascript"

def test_detect_typescript():
    assert detect_language("foo.ts") == "typescript"

def test_detect_go():
    assert detect_language("foo.go") == "go"

def test_detect_unknown():
    assert detect_language("foo.xyz") is None

def test_parse_python_function(tmp_path):
    f = tmp_path / "example.py"
    f.write_text("def hello(name: str) -> str:\n    return f'hello {name}'\n")
    defs, imports = parse_file(f)
    assert len(defs) == 1
    assert defs[0].name == "hello"
    assert defs[0].kind == "function"
    assert defs[0].line_start == 1
    assert defs[0].line_end == 2

def test_parse_python_class(tmp_path):
    f = tmp_path / "example.py"
    f.write_text("class Foo:\n    def bar(self):\n        pass\n")
    defs, imports = parse_file(f)
    kinds = {d.kind for d in defs}
    assert "class" in kinds
    names = {d.name for d in defs}
    assert "Foo" in names

def test_parse_python_imports(tmp_path):
    f = tmp_path / "example.py"
    f.write_text("from os.path import join\nimport sys\n")
    defs, imports = parse_file(f)
    modules = {imp.module for imp in imports}
    assert "os.path" in modules or "sys" in modules

def test_parse_javascript_function(tmp_path):
    f = tmp_path / "example.js"
    f.write_text("function greet(name) {\n  return `hello ${name}`;\n}\n")
    defs, imports = parse_file(f)
    assert len(defs) >= 1
    assert defs[0].name == "greet"
    assert defs[0].kind == "function"

def test_parse_go_function(tmp_path):
    f = tmp_path / "example.go"
    f.write_text("package main\n\nfunc Hello(name string) string {\n\treturn \"hello \" + name\n}\n")
    defs, imports = parse_file(f)
    assert len(defs) >= 1
    names = {d.name for d in defs}
    assert "Hello" in names

def test_parse_unsupported_returns_empty(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("a,b,c\n1,2,3\n")
    defs, imports = parse_file(f)
    assert defs == []
    assert imports == []
