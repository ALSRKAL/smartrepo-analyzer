"""Tests for the deep multi-language analysis engine."""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

from deep_analysis import parse_source


class TestGoParsing:
    src = textwrap.dedent("""\
        package main

        import (
            "fmt"
            "net/http"
        )

        // Server serves stuff.
        type Server struct {
            Port int
        }

        func (s *Server) Start() error {
            if s.Port == 0 {
                return fmt.Errorf("no port")
            }
            return nil
        }

        func Handler(w http.ResponseWriter, r *http.Request) {
            w.Write([]byte("ok")) // TODO validate input
        }
    """)

    def test_functions_with_complexity(self):
        p = parse_source(".go", "Go", self.src)
        names = {f.name for f in p.functions_detail}
        assert {"Start", "Handler"} <= names
        start = next(f for f in p.functions_detail if f.name == "Start")
        assert start.complexity == 2          # 1 + if
        assert start.exported is True         # capital letter

    def test_struct_and_imports(self):
        p = parse_source(".go", "Go", self.src)
        assert any(c.name == "Server" and c.kind == "struct" for c in p.classes_detail)
        assert {"fmt", "http"} <= set(p.imports)
        assert p.todos >= 1

    def test_keywords_inside_strings_not_counted(self):
        tricky = 'func A() {\n s := "if for while && ||"\n}\n'
        p = parse_source(".go", "Go", tricky)
        a = next(f for f in p.functions_detail if f.name == "A")
        assert a.complexity == 1


class TestRustParsing:
    def test_pub_fn_and_visibility(self):
        src = textwrap.dedent("""\
            pub struct Engine { pub size: u32 }
            impl Engine {
                /// Creates an engine.
                pub fn new(size: u32) -> Self {
                    if size == 0 { panic!("bad"); }
                    Engine { size }
                }
                fn hidden(&self) -> u32 {
                    for i in 0..self.size { }
                    self.size
                }
            }
        """)
        p = parse_source(".rs", "Rust", src)
        by_name = {f.name: f for f in p.functions_detail}
        assert set(by_name) == {"new", "hidden"}
        assert by_name["new"].exported is True
        assert by_name["hidden"].exported is False
        assert by_name["new"].complexity == 2
        assert by_name["hidden"].complexity == 2
        assert by_name["new"].documented is True   # /// doc comment


class TestJavaKotlin:
    def test_java_methods_classes(self):
        src = textwrap.dedent("""\
            import java.util.List;
            public class UserService extends BaseService implements Provider {
                public List<User> findActive(int limit, String sort) {
                    if (limit > 100 && sort != null) { limit = 100; }
                    return repo.query(limit, sort);
                }
                private void audit() {}
            }
        """)
        p = parse_source(".java", "Java", src)
        find = next(f for f in p.functions_detail if f.name == "findActive")
        assert find.args == 2 and find.exported is True and find.kind == "method"
        assert find.complexity >= 3              # if + &&
        cls = next(c for c in p.classes_detail if c.name == "UserService")
        assert "BaseService" in cls.bases
        assert any("java.util" in i for i in p.imports)

    def test_kotlin_fun(self):
        src = "class Repo {\n    suspend fun load(id: Int): User? {\n        return null\n    }\n}\n"
        p = parse_source(".kt", "Kotlin", src)
        assert any(f.name == "load" for f in p.functions_detail)
        assert any(c.name == "Repo" for c in p.classes_detail)


class TestJSTSDeep:
    src = textwrap.dedent("""\
        import React, { useState } from 'react';
        import axios from 'axios';
        import './local.css';

        export default function App(props) {
          const [n, setN] = useState(0);
          useEffect(() => { fetchItems(); }, []);
          if (n > 5) { setN(0); }
          return <div>{n}</div>;
        }

        const getUser = async (id) => {
          const res = await axios.get(`/api/${id}`);
          return res.data;
        };

        class Widget extends React.Component {
          render() { return null; }
        }

        module.exports = { App };
    """)

    def test_modern_syntax(self):
        p = parse_source(".jsx", "React JSX", self.src)
        names = {f.name for f in p.functions_detail}
        assert {"App", "getUser", "render"} <= names
        classes = {c.name for c in p.classes_detail}
        assert "Widget" in classes
        # local paths are excluded from package imports
        assert {"react", "axios"} <= set(p.imports)
        assert not any(i.startswith(".") or i == "local.css" for i in p.imports)

    def test_export_flags(self):
        p = parse_source(".js", "JavaScript", self.src)
        by_name = {f.name: f for f in p.functions_detail}
        assert by_name["App"].exported is True
        assert by_name["getUser"].exported is False   # plain const arrow

    def test_express_endpoints(self):
        src = "app.get('/health', h)\nrouter.post('/users', createUser)\n"
        p = parse_source(".js", "JavaScript", src)
        assert "GET /health" in p.endpoints
        assert "POST /users" in p.endpoints


class TestEndpointsPython:
    def test_flask_fastapi_decorators(self):
        src = textwrap.dedent('''\
            @app.get("/users/{id}")
            def get_user(id): ...

            @app.route("/home")
            def home(): ...

            @router.post("/items")
            def create(): ...
        ''')
        p = parse_source(".py", "Python", src)
        assert "GET /users/{id}" in p.endpoints
        assert "ANY /home" in p.endpoints
        assert "POST /items" in p.endpoints
        kinds = {f.name: f.kind for f in p.functions_detail}
        assert all(k == "endpoint" for k in kinds.values())


class TestPHPRubyDartSwift:
    def test_php(self):
        src = textwrap.dedent("""\
            use App\\Models\\User;
            class UserService extends Base {
                public function find(int $id): ?User {
                    if ($id < 1) { return null; }
                    return null;
                }
                private function log(string $m): void {}
            }
        """)
        p = parse_source(".php", "PHP", src)
        by_name = {f.name: f for f in p.functions_detail}
        assert by_name["find"].exported is True
        assert by_name["log"].exported is False
        assert by_name["find"].complexity == 2
        assert any(c.name == "UserService" and c.bases == ["Base"] for c in p.classes_detail)

    def test_ruby(self):
        src = textwrap.dedent("""\
            require 'json'
            class Greeter < Base
              # Says hello.
              def greet(name)
                if name.empty?
                  'hi'
                else
                  "hello #{name}"
                end
              end
            end
        """)
        p = parse_source(".rb", "Ruby", src)
        greet = next(f for f in p.functions_detail if f.name == "greet")
        assert greet.complexity >= 2
        assert greet.documented is True
        assert "json" in p.imports
        assert any(c.name == "Greeter" for c in p.classes_detail)

    def test_dart(self):
        src = textwrap.dedent("""\
            import 'package:flutter/material.dart';
            class MyPage extends StatelessWidget {
              Widget build(BuildContext ctx) {
                return Container();
              }
            }
        """)
        p = parse_source(".dart", "Dart", src)
        assert any(c.name == "MyPage" for c in p.classes_detail)
        assert any(f.name == "build" for f in p.functions_detail)


class TestTodosAndDocs:
    def test_todo_counting_python(self):
        src = "# TODO fix this\ndef a():\n    pass  # FIXME later\n"
        p = parse_source(".py", "Python", src)
        assert p.todos == 2

    def test_doc_coverage_signals(self):
        documented = '''/** Does the thing. */\nfunction doThing() {}\n'''
        p = parse_source(".js", "JavaScript", documented)
        assert p.functions_detail[0].documented is True


class TestRadonParity:
    """Lock in exact parity with radon (verified by cross-testing)."""

    def test_comprehension_filter_counts(self):
        p = parse_source(".py", "Python",
                         "def f(items):\n    return [x for x in items if x]\n")
        # base + generator + filter clause == radon's 3
        assert p.functions_detail[0].complexity == 3

    def test_assert_ignores_inner_boolops(self):
        p = parse_source(".py", "Python", "def f(a, b):\n    assert a or b\n")
        assert p.functions_detail[0].complexity == 2   # assert only, not `or`

    def test_async_for_counts_async_with_does_not(self):
        src = textwrap.dedent("""\
            async def fetch(s):
                async with s as t:
                    async for chunk in t:
                        yield chunk
        """)
        p = parse_source(".py", "Python", src)
        assert p.functions_detail[0].complexity == 2   # base + async for

    def test_match_cases_exclude_wildcard(self):
        src = textwrap.dedent("""\
            def f(x):
                match x:
                    case 1: return 1
                    case 2: return 2
                    case _: return 0
        """)
        p = parse_source(".py", "Python", src)
        assert p.functions_detail[0].complexity == 3   # base + 2 non-wildcard cases


class TestJsOperatorCounting:
    def test_short_circuit_operators_count(self):
        src = "function h(req, res){\n  const page = req.query.page || 1;\n}\n"
        p = parse_source(".js", "JavaScript", src)
        h = next(f for f in p.functions_detail if f.name == "h")
        assert h.complexity == 2   # base + ||


class TestDocstringFallback:
    def test_first_symbol_docstring_surfaces(self):
        src = "def greet(name):\n    \"\"\"مرحبًا بالعالم.\"\"\"\n    return name\n"
        p = parse_source(".py", "Python", src)
        assert "مرحبًا بالعالم" in p.docstring


class TestToolPathResolution:
    def test_finds_tool_beside_interpreter(self):
        from tool_runner import tool_path, reset_tool_cache
        reset_tool_cache()
        py = tool_path("python" if os.name != "nt" else "python")
        assert py is not None and Path(py).exists()

    def test_run_command_resolves_venv_tools(self):
        import sys as _sys
        from tool_runner import run_command
        proc = run_command([_sys.executable, "-c", "print('ok')"])
        assert proc is not None and "ok" in proc.stdout


class TestProjectIntegration:
    def test_metrics_include_intelligence(self, analyzed):
        structure, _ = analyzed
        m = structure.metrics
        assert "documented_symbols_pct" in m
        assert "total_todos" in m
        assert "complex_hotspots" in m
        assert "avg_function_args" in m
        assert isinstance(m.get("total_endpoints"), int)

    def test_ai_summary_has_code_intelligence(self, tmp_path, analyzed):
        import json
        structure, root = analyzed
        from smartrepo_analyzer import DocumentationGenerator

        out = tmp_path / "o"
        DocumentationGenerator(structure, out, project_root=root).generate_all()
        data = json.loads((out / "ai-summary.json").read_text(encoding="utf-8"))
        intel = data["code_intelligence"]
        assert "endpoints" in intel
        assert "public_api_surface" in intel
        assert "top_classes" in intel

    def test_health_uses_documentation_factor(self, analyzed):
        structure, _ = analyzed
        breakdown_keys = set(structure.health["breakdown"])
        assert "documentation" in breakdown_keys
