from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from installer.installer_core import install_verified_release, uninstall_nexa


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-directory", type=Path, required=True)
    parser.add_argument("--sample-file", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()

    app_directory = args.app_directory.resolve()
    with tempfile.TemporaryDirectory(prefix="Nexa Installer Smoke ") as temporary:
        root = Path(temporary) / "Nexa Program"
        package = Path(temporary) / "verified-release.zip"
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_STORED) as archive:
            for path in sorted(item for item in app_directory.rglob("*") if item.is_file()):
                archive.write(path, path.relative_to(app_directory).as_posix())

        install_verified_release(
            package,
            args.version,
            root,
            path_updater=lambda directory, add: None,
        )
        launcher = root / "bin" / "nexa.cmd"
        environment = os.environ.copy()
        environment["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32") + os.pathsep + os.environ["SystemRoot"]

        def run_nexa(*arguments: str) -> str:
            result = subprocess.run(
                [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", str(launcher), *arguments],
                cwd=args.sample_file.parent,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"nexa {' '.join(arguments)} failed with {result.returncode}: "
                    f"{result.stderr or result.stdout}"
                )
            return result.stdout

        version = run_nexa("--version")
        if f"Nexa {args.version}" not in version:
            raise RuntimeError(f"Unexpected version output: {version!r}")
        if "Verfügbare Befehle" not in run_nexa("help"):
            raise RuntimeError("The installed nexa.cmd did not forward the help command.")
        run_nexa("run", str(args.sample_file.resolve()))
        uninstall_nexa(root, path_updater=lambda directory, add: None)

    print("Installed nexa.cmd forwarded --version, help and run without Python on PATH.")
    print("The temporary installation was removed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
