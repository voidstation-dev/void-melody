"""Start the packaged API with only the desktop runtime environment."""

from __future__ import annotations

import os
import runpy
import sys
from collections.abc import Mapping


_WINDOWS_JOB_HANDLE = None


RUNTIME_ENVIRONMENT_NAMES = frozenset(
    {
        "PYTHONUNBUFFERED",
        "APP_ENV",
        "API_HOST",
        "API_PORT",
        "MELODY_API_TOKEN",
        "MELODY_DATA_DIR",
        "MELODY_CATALOG_PATH",
        "VIENEU_HF_HOME",
        "HF_HOME",
        "TTS_APPLY_RATE_WITH_FFMPEG",
        "TTS_QUEUE_CONCURRENCY",
        "TTS_CHUNK_CONCURRENCY",
    }
)

PYINSTALLER_RUNTIME_ENVIRONMENT_NAMES = frozenset(
    {
        # PyInstaller uses this to make a one-file child a fresh application
        # instance instead of reusing the current extraction directory.
        "PYINSTALLER_RESET_ENVIRONMENT",
    }
)

OS_RUNTIME_ENVIRONMENT_NAMES = frozenset(
    {
        # Needed to locate executables and create temporary files on macOS and
        # Windows. HOME and USERPROFILE are used by their respective platforms.
        "PATH",
        "TEMP",
        "TMP",
        "TMPDIR",
        "HOME",
        "USERPROFILE",
        # Windows requires its system directory for process startup. COMSPEC
        # and PATHEXT keep command and executable resolution intact.
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "PATHEXT",
    }
)


def _is_preserved_environment_name(name: str) -> bool:
    normalized_name = name.upper()
    return (
        name in RUNTIME_ENVIRONMENT_NAMES
        or normalized_name.startswith("_PYI_")
        or normalized_name in PYINSTALLER_RUNTIME_ENVIRONMENT_NAMES
        or normalized_name in OS_RUNTIME_ENVIRONMENT_NAMES
    )


def isolate_sidecar_environment(environ: Mapping[str, str]) -> dict[str, str]:
    """Return the desktop contract and safe PyInstaller/OS runtime state."""

    return {
        name: value
        for name, value in environ.items()
        if _is_preserved_environment_name(name)
    }


def _configure_windows_job() -> bool:
    """Keep every child in a kill-on-close Windows Job Object."""

    global _WINDOWS_JOB_HANDLE
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        class IoCounters(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_uint64),
                ("WriteOperationCount", ctypes.c_uint64),
                ("OtherOperationCount", ctypes.c_uint64),
                ("ReadTransferCount", ctypes.c_uint64),
                ("WriteTransferCount", ctypes.c_uint64),
                ("OtherTransferCount", ctypes.c_uint64),
            ]

        class BasicLimitInformation(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class ExtendedLimitInformation(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BasicLimitInformation),
                ("IoInfo", IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            wintypes.INT,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return False

        limits = ExtendedLimitInformation()
        # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        limits.BasicLimitInformation.LimitFlags = 0x00002000
        configured = kernel32.SetInformationJobObject(
            job,
            9,  # JobObjectExtendedLimitInformation
            ctypes.byref(limits),
            ctypes.sizeof(limits),
        )
        assigned = configured and kernel32.AssignProcessToJobObject(
            job,
            kernel32.GetCurrentProcess(),
        )
        if assigned:
            _WINDOWS_JOB_HANDLE = job
            return True
        else:
            kernel32.CloseHandle(job)
            return False
    except (AttributeError, OSError, ImportError):
        return False


def _isolate_packaged_process_tree() -> bool:
    if not getattr(sys, "frozen", False):
        return True
    if os.name == "nt":
        return _configure_windows_job()
    try:
        # A dedicated session/process group makes native shutdown atomic for
        # the sidecar and every child it creates on macOS.
        os.setsid()
        return True
    except OSError:
        return False


def main() -> None:
    runtime_environment = isolate_sidecar_environment(os.environ)
    os.environ.clear()
    os.environ.update(runtime_environment)
    if not _isolate_packaged_process_tree():
        raise RuntimeError("Unable to isolate packaged sidecar process tree")
    runpy.run_module("app.main", run_name="__main__")


if __name__ == "__main__":
    main()
