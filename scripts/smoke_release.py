"""Smoke test isolado do EXE RELEASE, sem impressão ou dados operacionais."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import win32api
import win32con
import win32event
import win32job
import win32process

from scripts.release_metadata import load_version
DEFAULT_EXECUTABLE = (
    PROJECT_ROOT
    / "release"
    / str(load_version(PROJECT_ROOT)["APP_VERSION"])
    / "Santa Rubi Label Studio.exe"
)

STILL_ACTIVE = 259


def run_smoke_test(executable: Path, wait_seconds: float = 5.0) -> dict[str, bool]:
    executable = executable.resolve(strict=True)

    with tempfile.TemporaryDirectory(prefix="SantaRubi-Release-Smoke-") as temporary:
        smoke_root = Path(temporary)
        local_app_data = smoke_root / "LocalAppData"
        isolated_temp = smoke_root / "Temp"
        local_app_data.mkdir()
        isolated_temp.mkdir()
        smoke_executable = smoke_root / executable.name
        shutil.copy2(executable, smoke_executable)

        environment = os.environ.copy()
        environment["LOCALAPPDATA"] = str(local_app_data)
        environment["TEMP"] = str(isolated_temp)
        environment["TMP"] = str(isolated_temp)

        startup = win32process.STARTUPINFO()
        startup.dwFlags |= win32process.STARTF_USESHOWWINDOW
        startup.wShowWindow = win32con.SW_HIDE

        job = win32job.CreateJobObject(None, "")
        info = win32job.QueryInformationJobObject(job, win32job.JobObjectExtendedLimitInformation)
        info["BasicLimitInformation"]["LimitFlags"] |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        win32job.SetInformationJobObject(job, win32job.JobObjectExtendedLimitInformation, info)

        process_handle = thread_handle = None
        try:
            process_handle, thread_handle, _process_id, _thread_id = win32process.CreateProcess(
                str(smoke_executable),
                None,
                None,
                None,
                False,
                win32process.CREATE_SUSPENDED,
                environment,
                str(smoke_root),
                startup,
            )
            win32job.AssignProcessToJobObject(job, process_handle)
            win32process.ResumeThread(thread_handle)
            time.sleep(wait_seconds)

            alive = win32process.GetExitCodeProcess(process_handle) == STILL_ACTIVE
            app_data_created = (local_app_data / "Santa Rubi Label Studio").is_dir()
            return {
                "started_and_alive": alive,
                "isolated_app_data_created": app_data_created,
                "independent_working_directory": smoke_root != executable.parent,
            }
        finally:
            # O one-file usa um processo pai e um filho. Encerra o Job de
            # forma síncrona e aguarda as DLLs extraídas serem liberadas antes
            # de o TemporaryDirectory tentar apagar a pasta _MEI.
            win32job.TerminateJobObject(job, 0)
            if process_handle is not None:
                win32event.WaitForSingleObject(process_handle, 5000)
                win32api.CloseHandle(process_handle)
            if thread_handle is not None:
                win32api.CloseHandle(thread_handle)
            time.sleep(2.0)
            win32api.CloseHandle(job)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "executable",
        nargs="?",
        type=Path,
        default=DEFAULT_EXECUTABLE,
    )
    args = parser.parse_args()
    result = run_smoke_test(args.executable)
    for key, value in result.items():
        print(f"{key}={value}")
    return 0 if all(result.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
