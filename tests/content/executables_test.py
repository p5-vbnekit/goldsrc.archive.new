#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest

assert "__main__" != __name__


@pytest.fixture(scope = "module")
def module_context(session_context):
    import os
    import re
    import shlex
    import pathlib
    import subprocess

    _config = session_context.config
    _make_property_collector = session_context.auxiliary_module.common.property_collector.make

    def _patterns():
        _known = dict(
            linux = ("hltv", "hlds_run", "hlds_linux", re.compile(r"^.+\.so(\.[0-9]+){0,3}$")),
            windows = (re.compile(r"^hlds\.exe$", re.IGNORECASE), re.compile(r"^.+\.dll$", re.IGNORECASE)),
            darwin = (re.compile(r"^.+\.dylyb$", re.IGNORECASE), )
        )
        _collector = _make_property_collector(
            aliens = list(), required = _known.pop(_config.system)
        )
        for _known in _known.values(): _collector.aliens.extend(_known)
        return _collector

    _patterns = _patterns()

    _content_path = _config.content

    def _match(path: str, patterns: str | re.Pattern):
        for _pattern in patterns:
            if isinstance(_pattern, str):
                if _pattern == path: return True
                continue
            assert isinstance(_pattern, re.Pattern)
            if _pattern.match(path) is not None: return True
        return False

    def _generate_aliens(): yield from filter(lambda path: _match(
        path = path.relative_to(_content_path).as_posix(),
        patterns = _patterns.aliens
    ), _content_path.rglob("*"))

    _upstream_ref = _config.upstream

    def _generate_required():
        _content = subprocess.check_output((
            "git", "ls-tree", "-r", "--name-only", _upstream_ref, "--", "."
        ), stdin = subprocess.DEVNULL, cwd = _content_path.as_posix(), universal_newlines = True)

        assert isinstance(_content, str)
        _content = _content.strip()
        assert _content
        _set = set()

        for _content in _content.splitlines(keepends = False):
            assert _content
            assert _content not in _set
            _set.add(_content)
            assert not pathlib.Path(_content).is_absolute()
            if _match(path = _content, patterns = _patterns.required): yield _content

    def _make_upstream_controller():
        def _validate_path(value: pathlib.PurePath):
            assert isinstance(value, pathlib.PurePath)
            value = pathlib.PurePosixPath(value)
            assert not value.is_absolute()
            return value.as_posix()

        def _read(path: pathlib.Path):
            _content = subprocess.check_output((
                "git", "show", f"{_upstream_ref}:./{_validate_path(value = path)}"
            ), stdin = subprocess.DEVNULL, cwd = _content_path.as_posix(), text = False)
            assert isinstance(_content, bytes)
            return _content

        def _is_binary(path: pathlib.Path):
            path = _validate_path(value = path)
            _response = subprocess.run(
                ("git", "grep", "-I", "--no-color", "--name-only", "", _upstream_ref, "--", f"./{path}"),
                stdin = subprocess.DEVNULL, stdout = subprocess.PIPE,
                cwd = _content_path.as_posix(), universal_newlines = True
            )
            assert isinstance(_response.stdout, str)
            assert isinstance(_response.returncode, int)
            if 0 == _response.returncode:
                _response, = _response.stdout.splitlines(keepends = False)
                assert _response == f"{_upstream_ref}:{path}"
                return False
            assert 1 == _response.returncode
            assert not _response.stdout
            return True

        def _is_symlink(path: pathlib.Path):
            _content = subprocess.check_output((
                "git", "ls-files", "--format=%(objectmode)",
                _upstream_ref, "--", f"./{_validate_path(value = path)}"
            ), stdin = subprocess.DEVNULL, cwd = _content_path.as_posix(), universal_newlines = True)
            assert isinstance(_content, str)
            _content = _content.strip()
            assert _content
            _content, = _content.splitlines(keepends = False)
            _content = int(_content)
            assert 0 <= _content
            return 120000 == _content

        def _has_sensitive_changes(path: pathlib.Path):
            path = _validate_path(value = path)
            _response = subprocess.run(
                ("git", "diff", "--exit-code", "--ignore-all-space", "--ignore-cr-at-eol", _upstream_ref, "--", f"./{path}"),
                stdin = subprocess.DEVNULL, stdout = subprocess.PIPE,
                cwd = _content_path.as_posix(), universal_newlines = True
            )
            assert isinstance(_response.stdout, str)
            assert isinstance(_response.returncode, int)
            if 0 == _response.returncode:
                assert not _response.stdout
                return False
            assert 1 == _response.returncode
            assert _response.stdout
            return True

        return _make_property_collector(
            ref = _upstream_ref, read = _read, is_binary = _is_binary,
            is_symlink = _is_symlink, has_sensitive_changes = _has_sensitive_changes
        )

    return _make_property_collector(
        content = _content_path, upstream = _make_upstream_controller(),
        modules = _make_property_collector(os = os, shlex = shlex, pathlib = pathlib),
        generators = _make_property_collector(aliens = _generate_aliens, required = _generate_required)
    )


def test_aliens(subtests, module_context):
    for _path in module_context.generators.aliens():
        with subtests.test(path = _path): assert False, "alien found"


def test_required(subtests, module_context):
    _modules = module_context.modules
    _upstream = module_context.upstream
    _content_path = module_context.content

    for _path in module_context.generators.required():
        with subtests.test(path = _path):
            _path = _modules.pathlib.Path(_path)

            _absolute = _content_path / _path

            if _absolute.is_symlink():
                assert _upstream.is_symlink(path = _path), "changed to symlink"
                _content = _upstream.read(path = _path).decode("utf-8")
                assert _modules.os.readlink(_absolute) == _content, "symlink changed"
                continue

            assert _absolute.resolve(strict = True) == _absolute
            assert _absolute.is_relative_to(_content_path)
            assert _absolute.is_file(), "not regular"

            if _upstream.is_binary(path = _path):
                with open(_absolute, "rb") as _content: _content = _content.read()
                assert _content == _upstream.read(path = _path), "content changed"
                continue

            assert not _upstream.has_sensitive_changes(path = _path), "content changed: {}".format(_modules.shlex.join((
                "git", "diff", "--ignore-all-space", "--ignore-cr-at-eol", _upstream.ref, "--", f"./contents/{_path}"
            )))
