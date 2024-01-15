#!/usr/bin/env python3
# -*- coding: utf-8 -*-

assert "__main__" != __name__


def _private():
    import pytest
    import pathlib
    import platform
    import subprocess

    import _auxiliary as _auxiliary_module

    _make_property_collector = _auxiliary_module.common.property_collector.make

    _known_systems = ("linux", "windows", "darwin")

    def _validate_system(value: str):
        assert isinstance(value, str)
        if str is not type(value): value = str(value)
        value = value.lower()
        assert value in _known_systems
        return value

    _platform_system = _validate_system(value = platform.system())

    def _initialize_cli(parser):
        parser.addoption(
            "--tests.system", default = _platform_system,
            help = "system type [{}]".format("|".join(_known_systems))
        )
        parser.addoption("--tests.content", required = False, default = None, help = "content directory")
        parser.addoption("--tests.upstream", required = True, help = "upstream git ref")
        parser.addoption("--tests.pass-alien-upstream", action = "store_true", help = "allow non-ancestor upstream")

    def _make_fixture(request):
        def _make_config():
            def _system(): return _validate_system(value = request.config.getoption("--tests.system"))

            _system = _system()

            def _content():
                _value = request.config.getoption("--tests.content")
                if _value is None:
                    _value = pathlib.Path(__file__).resolve(strict = True)
                    assert _value.is_file()
                    assert 3 < len(_value.parts)
                    _value = _value / "../../content"

                else:
                    assert isinstance(_value, str)
                    if str is not type(_value): _value = str(_value)

                _value = pathlib.Path(_value).resolve(strict = True)
                _required = _value / "valve"
                assert _required.resolve(strict = True) == _required
                _required = _required / "dlls"
                assert _required.resolve(strict = True) == _required
                for _required in _required.glob("*"): break
                else: raise ValueError("invalid content directory: valve/dlls is empty")
                return _value

            _content = _content()

            def _upstream():
                def _strict():
                    _value = request.config.getoption("--tests.pass-alien-upstream")
                    assert isinstance(_value, bool)
                    return not _value

                _strict = _strict()

                def _ref():
                    _value = request.config.getoption("--tests.upstream")
                    assert isinstance(_value, str)
                    if str is not type(_value): _value = str(_value)
                    assert _value
                    assert _value.strip() == _value
                    _value, = _value.splitlines(keepends = False)
                    _type = subprocess.check_output((
                        "git", "cat-file", "-t", _value
                    ), stdin = subprocess.DEVNULL, cwd = _content, universal_newlines = True)
                    assert isinstance(_type, str)
                    _type, = _type.splitlines(keepends = False)
                    assert "commit" == _type
                    _value = subprocess.check_output((
                        "git", "rev-parse", "--verify", _value
                    ), stdin = subprocess.DEVNULL, cwd = _content, universal_newlines = True)
                    assert isinstance(_value, str)
                    _value, = _value.splitlines(keepends = False)
                    assert _value.strip() == _value
                    if _strict: assert not subprocess.check_output((
                        "git", "merge-base", "--is-ancestor", _value, "HEAD"
                    ), stdin = subprocess.DEVNULL, cwd = _content, text = False)
                    return _value

                return _ref()

            _upstream = _upstream()

            return _make_property_collector(
                system = _system,
                content = _content,
                upstream = _upstream
            )

        return _make_property_collector(
            auxiliary_module = _auxiliary_module,
            config = _make_config(),
            system = _platform_system
        )

    return _make_property_collector(
        pytest_module = pytest,
        make_fixture = _make_fixture,
        initialize_cli = _initialize_cli
    )


_private = _private()


def pytest_addoption(parser): _private.initialize_cli(parser = parser)


@_private.pytest_module.fixture(scope = "session")
def session_context(request): return _private.make_fixture(request = request)
