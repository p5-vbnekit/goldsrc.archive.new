#!/usr/bin/env python3

if "__main__" == __name__:
    def _main():
        import os
        import io
        import sys
        import typing
        import asyncio
        import inspect

        _windows = ("nt" == os.name)

        def _protocol():
            _executable, _id = sys.argv[1:3]
            assert isinstance(_executable, str)
            assert _executable
            assert isinstance(_id, str)
            _id = int(_id)
            assert 0 < _id
            _request = ["+app_update", str(_id)]
            for _option in sys.argv[2:]:
                assert isinstance(_option, str)
                _option = _option.strip()
                assert _option
                _request.append(_option)
            _request.append("validate")
            _request = "+login anonymous", " ".join(_request), "+quit"
            class _Result(object):
                executable = _executable
                request = _request
                response = f"Success! App '{_id}' fully installed."
            return _Result

        _protocol = _protocol()

        class _NotCriticalException(RuntimeError): pass
        class _ReturnCodeException(_NotCriticalException): pass
        class _UnexpectedResponseException(_NotCriticalException): pass

        class _StdoutValidator(object):
            @property
            def state(self): return self.__state

            def __call__(self, data: str = None):
                if data is None:
                    self.__state = self.__valid is True
                    return self.__state
                assert isinstance(data, str)
                assert self.__state is None
                if self.__valid is True:
                    if self.__response_should_be_last or (_protocol.response == data): self.__valid = False
                elif self.__valid is None:
                    if _protocol.response == data: self.__valid = True
                return None

            def __init__(self):
                super().__init__()
                self.__state = None
                self.__valid = None

            __response_should_be_last = not _windows

        async def _read_coroutine(stream: asyncio.StreamReader, delegate: typing.Callable):
            assert isinstance(stream, asyncio.StreamReader)
            assert callable(delegate)
            while True:
                _data = await stream.readline()
                assert isinstance(_data, bytes)
                if not _data: break
                _data = delegate(_data.decode("utf-8").strip())
                if inspect.isawaitable(_data): await _data

        def _stderr_handler(data: str):
            assert isinstance(data, str)
            if data: print(data, flush = True, file = sys.stderr)

        async def _iteration_coroutine():
            _validator = _StdoutValidator()

            def _stdout_handler(data: str):
                assert isinstance(data, str)
                if data: print(data, flush = True, file = sys.stdout)
                _validator(data = data)

            _subprocess = await asyncio.subprocess.create_subprocess_exec(
                _protocol.executable, *_protocol.request,
                stdin = asyncio.subprocess.DEVNULL, stdout = asyncio.subprocess.PIPE, stderr = asyncio.subprocess.PIPE
            )
            _io_tasks = (
                asyncio.create_task(_read_coroutine(stream = _subprocess.stdout, delegate = _stdout_handler)),
                asyncio.create_task(_read_coroutine(stream = _subprocess.stderr, delegate = _stderr_handler))
            )

            await asyncio.gather(*_io_tasks)
            await _subprocess.wait()
            assert isinstance(_subprocess.returncode, int)

            try: assert 0 == _subprocess.returncode
            except AssertionError: raise _ReturnCodeException()

            try: assert _validator()
            except AssertionError: raise _UnexpectedResponseException()

        async def _main_coroutine():
            _attempt = 0
            _attempts = 6

            while True:
                _attempt += 1
                print(f"attempt {_attempt} of {_attempts}", flush = True, file = sys.stderr)
                try: await _iteration_coroutine()
                except _NotCriticalException:
                    if _attempts > _attempt: continue
                    raise
                break

        if _windows: asyncio.set_event_loop(asyncio.ProactorEventLoop())
        asyncio.get_event_loop().run_until_complete(_main_coroutine())

    _main()
