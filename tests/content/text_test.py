#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest

assert "__main__" != __name__


@pytest.fixture(scope = "module")
def module_context(session_context):
    import magic
    import pathlib
    import subprocess

    _make_property_collector = session_context.auxiliary_module.common.property_collector.make

    _mime_magic = _make_property_collector(
        type = magic.Magic(mime = True).from_file,
        encoding = magic.Magic(mime_encoding = True).from_file
    )

    _root = session_context.config.content

    def _validate_reader_path(value: str):
        assert isinstance(value, str)
        assert value
        value, = value.splitlines(keepends = True)
        _value = pathlib.PurePosixPath(value)
        assert _value.as_posix() == value
        assert not _value.is_absolute()
        return value

    def _make_reader(path: str, encoding: str):
        path = _validate_reader_path(value = path)

        def _read(decode: bool = False, upstream: bool = False):
            assert isinstance(decode, bool)
            assert isinstance(upstream, bool)
            if not upstream:
                _content = dict(mode = "r", encoding = encoding) if decode else dict(mode = "rb")
                with open(_root / path, **_content) as _content: return _content.read()
            _content = subprocess.check_output((
                "git", "show", f"{session_context.config.upstream}:./{path}"
            ), stdin = subprocess.DEVNULL, cwd = _root, text = False)
            assert isinstance(_content, bytes)
            if decode: _content = _content.decode(encoding)
            return _content

        return _read

    def _files():
        _unique = set()
        _response = subprocess.check_output(
            ("git", "grep", "-I", "--no-color", "--no-index", "--name-only", ""),
            stdin = subprocess.DEVNULL, cwd = _root.as_posix(), universal_newlines = True
        )
        assert isinstance(_response, str)
        _response = _response.strip()
        assert _response
        for _path in _response.splitlines(keepends = False):
            assert _path
            assert _path not in _unique
            _unique.add(_path)
            _absolute = _root / _path
            assert not _absolute.is_symlink()
            assert _absolute.resolve(strict = True) == _absolute
            _encoding = _mime_magic.encoding(_absolute)
            assert _encoding
            yield _make_property_collector(
                path = _path, mime = _mime_magic.type(_absolute), encoding = _encoding,
                read = _make_reader(path = _path, encoding = _encoding)
            )
        for _path in _root.rglob("*"):
            if _path.is_symlink(): continue
            if not _path.is_file(): continue
            _relative = _path.relative_to(_root).as_posix()
            if _relative in _unique: continue
            _encoding = _mime_magic.encoding(_path)
            if "binary" == _encoding: continue
            yield _make_property_collector(
                path = _relative, mime = _mime_magic.type(_path), encoding = _encoding,
                read = _make_reader(path = _relative, encoding = _encoding)
            )

    _files = tuple(_files())

    _utf16le_feff = (
        "valve/resource/valve_english.txt",
        "valve/resource/gameui_english.txt",
        "cstrike/resource/cstrike_english.txt"
    )

    return _make_property_collector(
        root = _root, files = _files,
        utf16le_feff = _utf16le_feff,
        system = session_context.system
    )


def test_type(subtests, module_context):
    for _content in module_context.files:
        with subtests.test(path = _content.path): assert _content.mime in {
            "text/plain", "text/html", "text/x-shellscript"
        }


def test_encoding(subtests, module_context):
    def _known():
        _collector = dict()

        for _encoding, _path in {
            "utf-8": ("cstrike/manual/manual.htm", ),
            "utf-16le": module_context.utf16le_feff
        }.items():
            for _path in _path:
                assert _path not in _collector
                _collector[_path] = _encoding

        return _collector

    _known = _known()

    for _content in module_context.files:
        with subtests.test(path = _content.path):
            try: _encoding = _known.pop(_content.path)
            except KeyError: _encoding = "us-ascii"
            assert _encoding == _content.encoding
            _data = _content.read(decode = False, upstream = False)
            assert _data == _data.decode(_encoding).encode(_encoding)

    assert not _known, "missing known files"


def test_utf16le_feff(subtests, module_context):
    for _content in module_context.utf16le_feff:
        with subtests.test(path = _content):
            _content = (module_context.root / _content).resolve(strict = True)
            assert _content.is_file()
            with open(_content, mode = "r", encoding = "utf-16le") as _content:
                assert "\ufeff" == _content.read(1)


def test_vdf(subtests, module_context):
    import re
    import vdf

    def _match():
        _patterns = [re.compile(
            fr"^.+\.{re.escape(_patterns)}$", re.IGNORECASE
        ) for _patterns in (r"vdf", r"res", r"txt")]

        def _result(content):
            for _pattern in _patterns:
                if _pattern.match(content.path) is None: continue
                if "text/plain" != content.mime: continue
                if content.encoding.startswith("unknown-"): continue
                return True
            return False

        return _result

    _match = _match()

    def _make_dry():
        _spaces_pattern = re.compile(r"\s+")

        def _generator(content: str, brutal: bool):
            for content in content.splitlines(keepends = False):
                content = content.strip()
                if not content: continue
                if brutal: content = _spaces_pattern.sub(" ", content)
                yield content

        return lambda *args, **kwargs: "\n".join(_generator(*args, **kwargs))

    _make_dry = _make_dry()

    def _sort(content):
        _type = type(content)
        _collector = _type()
        for _key, _value in sorted({**content}.items()):
            if isinstance(_value, _type): _value = _sort(content = _value)
            _collector[_key] = _value
        return _collector

    def _load(content, upstream: bool):
        _path = content.path

        if content.path.lower().endswith(".txt"):
            _encoding = content.encoding
            content = content.read(decode = False, upstream = upstream)
            try: content = content.decode(_encoding)
            except UnicodeDecodeError: return None
            content = _make_dry(content = content, brutal = True)
            try: content = vdf.loads(content)
            except SyntaxError: return None

        else:
            assert "text/plain" == content.mime
            assert "us-ascii" == content.encoding
            content = vdf.loads(_make_dry(content = content.read(
                decode = True, upstream = upstream
            ), brutal = False))

        if _path in {
            "valve/spectcammenu.txt",
            "cstrike/spectcammenu.txt"
        }: content = _sort(content = content)

        return content

    for _content in filter(_match, module_context.files):
        with subtests.test(path = _content.path):
            _local = _load(content = _content, upstream = False)
            _upstream = _load(content = _content, upstream = True)
            if _local is None: assert _upstream is None
            elif _upstream is None: pytest.skip("parsed as non-vdf in upstream")
            else: assert vdf.dumps(_local) == vdf.dumps(_upstream)


def test_endings(subtests, module_context):
    import re

    _valid = dict(linux = {"\n"}, windows = {"\n", "\r\n"}, darwin = {"\n", "\r", "\r\n"})[module_context.system]
    _pattern = re.compile("[\n\r]")

    def _make_ending(value: bytes):
        for _match in _pattern.finditer(value): return value[_match.start():]
        return None

    for _content in module_context.files:
        with subtests.test(path = _content.path):
            for _data in _content.read(
                decode = True, upstream = False
            ).splitlines(keepends = True): assert _make_ending(value = _data) in _valid
            else: continue
            assert _data.rstrip(), "trailing empty lines"


def test_spaces(subtests, module_context):
    for _content in module_context.files:
        with subtests.test(path = _content.path):
            for _data in _content.read(
                decode = True, upstream = False
            ).splitlines(keepends = False):
                assert "\t" not in _data, "tabs"
                assert _data.rstrip() == _data, "trailing spaces"
