#!/usr/bin/env python3
# -*- coding: utf-8 -*-

assert "__main__" != __name__


def test(subtests, session_context):
    import pytest
    import pathlib

    if "windows" == session_context.system: pytest.skip("not available for windows")

    _root_path = session_context.config.content

    def _generate_expectations():
        _make_property_collector = session_context.auxiliary_module.common.property_collector.make

        _extended = set((_root_path / _path).as_posix() for _path in dict(
            linux = ("hltv", "hlds_run", "hlds_linux"),
            windows = tuple(), darwin = tuple()
        )[session_context.config.system])

        def _make_mode(path: pathlib.Path):
            if path.is_symlink(): return None
            if path.is_dir(): return 0o40755
            if _path.as_posix() in _extended: return 0o100755
            return 0o100644

        def _make_item(path: pathlib.Path):
            _mode = _make_mode(path = path)
            if _mode is None: return None
            return _make_property_collector(path = path, mode = _mode)

        yield _make_item(_root_path)

        for _path in _root_path.rglob("*"):
            _item = _make_item(_path)
            if _item is None: continue
            yield _item

    _root_stat = _root_path.stat()

    for _expectation in _generate_expectations():
        with subtests.test(path = _expectation.path.as_posix()):
            _stat = _expectation.path.stat()
            assert _root_stat.st_uid == _stat.st_uid
            assert _root_stat.st_gid == _stat.st_gid
            assert _stat.st_mode == _expectation.mode
