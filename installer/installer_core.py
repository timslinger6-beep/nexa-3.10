from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable

APP_ID = "Nexa.WindowsInstaller"
INSTALLER_VERSION = "1.0.0"
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_SIGNATURE_BYTES = 1024
MAX_PACKAGE_BYTES = 2 * 1024 * 1024 * 1024
MAX_UNPACKED_BYTES = 3 * 1024 * 1024 * 1024
MAX_ARCHIVE_FILES = 20_000
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def _version_tuple(version: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in version.split("."))


class ReleaseError(RuntimeError):
    """A release could not be downloaded, verified, or installed safely."""


def _duplicate_key_guard(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReleaseError(f"Doppelter JSON-Schlüssel: {key}")
        result[key] = value
    return result


def _is_private_or_local_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    hostname = hostname.lower()
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        address = ipaddress.ip_address(hostname)
        return address.is_private or address.is_loopback or address.is_link_local
    except ValueError:
        return False


def _require_https(url: str) -> urllib.parse.SplitResult:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.lower() == "https" and parsed.hostname:
        if parsed.username or parsed.password or parsed.fragment:
            raise ReleaseError("Release-URLs mit Zugangsdaten oder Fragmenten sind unzulässig.")
        return parsed
    if parsed.scheme.lower() == "http" and parsed.hostname and _is_private_or_local_host(parsed.hostname):
        if parsed.username or parsed.password or parsed.fragment:
            raise ReleaseError("Release-URLs mit Zugangsdaten oder Fragmenten sind unzulässig.")
        return parsed
    raise ReleaseError("Release-URLs müssen HTTPS oder eine lokale/private HTTP-URL verwenden.")


def _same_origin(url: str, origin: urllib.parse.SplitResult) -> None:
    parsed = _require_https(url)
    if (parsed.hostname.lower(), parsed.port or (443 if parsed.scheme.lower() == 'https' else 80)) != (
        origin.hostname.lower(),
        origin.port or (443 if origin.scheme.lower() == 'https' else 80),
    ):
        raise ReleaseError("Manifest und Paket müssen vom selben Server stammen.")


def load_config(config_path: Path) -> dict[str, str]:
    try:
        config = json.loads(
            config_path.read_text(encoding="utf-8-sig"),
            object_pairs_hook=_duplicate_key_guard,
        )
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseError(f"Release-Konfiguration konnte nicht gelesen werden: {error}") from error

    if not isinstance(config, dict):
        raise ReleaseError("Die Release-Konfiguration muss ein JSON-Objekt sein.")
    manifest_url = config.get("manifest_url")
    public_key = config.get("ed25519_public_key")
    if not isinstance(manifest_url, str) or not isinstance(public_key, str):
        raise ReleaseError("manifest_url oder ed25519_public_key fehlt in der Konfiguration.")

    _require_https(manifest_url)
    if not public_key:
        raise ReleaseError(
            "Der Release-Signaturschlüssel ist noch nicht konfiguriert. "
            "Bitte installer/release-config.json mit dem öffentlichen Ed25519-Schlüssel "
            "des Release-Servers bauen."
        )
    try:
        decoded_key = base64.b64decode(public_key, validate=True)
    except ValueError as error:
        raise ReleaseError("Der öffentliche Ed25519-Schlüssel ist ungültiges Base64.") from error
    if len(decoded_key) != 32:
        raise ReleaseError("Ein Ed25519-Schlüssel muss genau 32 Bytes lang sein.")
    return {"manifest_url": manifest_url, "ed25519_public_key": public_key}


def _read_response(url: str, maximum_bytes: int, origin: urllib.parse.SplitResult) -> bytes:
    _same_origin(url, origin)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": f"NexaInstaller/{INSTALLER_VERSION}", "Accept": "*/*"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            _same_origin(response.geturl(), origin)
            length_header = response.headers.get("Content-Length")
            if length_header and int(length_header) > maximum_bytes:
                raise ReleaseError(f"Download überschreitet das Größenlimit: {url}")
            data = response.read(maximum_bytes + 1)
    except ReleaseError:
        raise
    except Exception as error:
        raise ReleaseError(f"HTTPS-Download fehlgeschlagen ({url}): {error}") from error
    if len(data) > maximum_bytes:
        raise ReleaseError(f"Download überschreitet das Größenlimit: {url}")
    return data


def _manifest_signature_url(manifest_url: str) -> str:
    parsed = urllib.parse.urlsplit(manifest_url)
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path + ".sig", parsed.query, "")
    )


def verify_manifest(
    manifest_bytes: bytes,
    signature_bytes: bytes,
    public_key_base64: str,
) -> dict:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as error:
        raise ReleaseError(
            "Signaturprüfung nicht verfügbar. Der Installer wurde unvollständig gebaut."
        ) from error
    try:
        public_key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(public_key_base64, validate=True)
        )
        signature = base64.b64decode(signature_bytes.strip(), validate=True)
        public_key.verify(signature, manifest_bytes)
    except (ValueError, InvalidSignature) as error:
        raise ReleaseError("Die Release-Signatur ist ungültig.") from error

    try:
        manifest = json.loads(
            manifest_bytes.decode("utf-8"),
            object_pairs_hook=_duplicate_key_guard,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReleaseError(f"Das signierte Manifest enthält ungültiges JSON: {error}") from error

    if not isinstance(manifest, dict) or manifest.get("schema") != 1:
        raise ReleaseError("Unbekanntes Release-Manifest-Schema.")
    releases = manifest.get("releases")
    if not isinstance(releases, list) or not releases:
        raise ReleaseError("Das Manifest enthält keine Releases.")

    seen_versions: set[str] = set()
    validated = []
    for release in releases:
        if not isinstance(release, dict):
            raise ReleaseError("Ungültiger Release-Eintrag im Manifest.")
        version = release.get("version")
        if not isinstance(version, str) or not VERSION_PATTERN.fullmatch(version):
            raise ReleaseError("Ungültige Release-Version im Manifest.")
        if version in seen_versions:
            raise ReleaseError(f"Doppelte Release-Version im Manifest: {version}")
        seen_versions.add(version)
        if release.get("platform") != "windows-x64":
            continue
        package_url = release.get("package_url")
        package_hash = release.get("sha256")
        package_size = release.get("size")
        minimum_installer = release.get("min_installer", "1.0.0")
        if not isinstance(package_url, str):
            raise ReleaseError(f"Paket-URL fehlt für Nexa {version}.")
        if not isinstance(package_hash, str) or not SHA256_PATTERN.fullmatch(package_hash):
            raise ReleaseError(f"Ungültige SHA-256-Prüfsumme für Nexa {version}.")
        if (
            not isinstance(package_size, int)
            or isinstance(package_size, bool)
            or not 0 < package_size <= MAX_PACKAGE_BYTES
        ):
            raise ReleaseError(f"Ungültige Paketgröße für Nexa {version}.")
        if (
            not isinstance(minimum_installer, str)
            or not VERSION_PATTERN.fullmatch(minimum_installer)
        ):
            raise ReleaseError(f"Ungültige Mindest-Installer-Version für Nexa {version}.")
        _require_https(package_url)
        validated.append(
            {
                "version": version,
                "platform": "windows-x64",
                "package_url": package_url,
                "sha256": package_hash,
                "size": package_size,
                "min_installer": minimum_installer,
            }
        )
    if not validated:
        raise ReleaseError("Das signierte Manifest enthält kein Release für Windows x64.")
    manifest["releases"] = validated
    manifest["latest"] = manifest.get("latest")
    latest = manifest.get("latest")
    if not isinstance(latest, str) or latest not in {
        release["version"] for release in validated
    }:
        raise ReleaseError("Die als latest markierte Version ist kein verfügbares Windows-x64-Release.")
    if any(
        _version_tuple(release["min_installer"]) > _version_tuple(INSTALLER_VERSION)
        for release in validated
    ):
        raise ReleaseError("Das Release benötigt eine neuere Version des Installers.")
    return manifest


def fetch_manifest(config: dict[str, str]) -> dict:
    manifest_url = config["manifest_url"]
    origin = _require_https(manifest_url)
    manifest_bytes = _read_response(manifest_url, MAX_MANIFEST_BYTES, origin)
    signature_bytes = _read_response(
        _manifest_signature_url(manifest_url), MAX_SIGNATURE_BYTES, origin
    )
    manifest = verify_manifest(
        manifest_bytes,
        signature_bytes,
        config["ed25519_public_key"],
    )
    for release in manifest["releases"]:
        _same_origin(release["package_url"], origin)
    return manifest


def _verify_package_file(path: Path, release: dict) -> None:
    if path.stat().st_size != release["size"]:
        raise ReleaseError("Die heruntergeladene Paketgröße stimmt nicht mit dem signierten Manifest überein.")
    digest = hashlib.sha256()
    with path.open("rb") as package:
        for chunk in iter(lambda: package.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != release["sha256"]:
        raise ReleaseError("Die SHA-256-Prüfsumme des Nexa-Pakets stimmt nicht.")


def download_package(
    release: dict,
    destination: Path,
    progress: Callable[[int, int], None] | None = None,
) -> Path:
    origin = _require_https(release["package_url"])
    _same_origin(release["package_url"], origin)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".partial")
    digest = hashlib.sha256()
    downloaded = 0
    try:
        request = urllib.request.Request(
            release["package_url"],
            headers={"User-Agent": f"NexaInstaller/{INSTALLER_VERSION}"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            _same_origin(response.geturl(), origin)
            length_header = response.headers.get("Content-Length")
            if length_header and int(length_header) != release["size"]:
                raise ReleaseError("Die angekündigte Paketgröße ist unerwartet.")
            with partial.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    downloaded += len(chunk)
                    if downloaded > release["size"] or downloaded > MAX_PACKAGE_BYTES:
                        raise ReleaseError("Der Paketdownload überschreitet die signierte Größe.")
                    output.write(chunk)
                    digest.update(chunk)
                    if progress:
                        progress(downloaded, release["size"])
        if downloaded != release["size"]:
            raise ReleaseError("Der Paketdownload ist unvollständig.")
        if digest.hexdigest() != release["sha256"]:
            raise ReleaseError("Die SHA-256-Prüfsumme des Nexa-Pakets stimmt nicht.")
        os.replace(partial, destination)
        return destination
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def _safe_archive_target(root: Path, name: str) -> Path:
    if not name or "\\" in name or name.startswith("/") or "\x00" in name:
        raise ReleaseError(f"Unsicherer Pfad im Release-Archiv: {name!r}")
    relative = PurePosixPath(name)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ReleaseError(f"Unsicherer Pfad im Release-Archiv: {name!r}")
    for part in relative.parts:
        if ":" in part or part.endswith((".", " ")):
            raise ReleaseError(f"Ungültiger Windows-Pfad im Release-Archiv: {name!r}")
        if part.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES:
            raise ReleaseError(f"Reservierter Windows-Pfad im Release-Archiv: {name!r}")
    target = root.joinpath(*relative.parts)
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise ReleaseError(f"Archivpfad verlässt das Installationsverzeichnis: {name!r}") from error
    return target


def extract_verified_package(
    archive_path: Path,
    destination: Path,
    progress: Callable[[int, int], None] | None = None,
) -> list[str]:
    if destination.exists():
        raise ReleaseError(f"Das temporäre Installationsverzeichnis existiert bereits: {destination}")
    destination.mkdir(parents=True)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.infolist()
            if len(members) > MAX_ARCHIVE_FILES:
                raise ReleaseError("Das Release-Archiv enthält zu viele Dateien.")
            total_size = sum(member.file_size for member in members)
            if total_size > MAX_UNPACKED_BYTES:
                raise ReleaseError("Das entpackte Release überschreitet das Größenlimit.")
            seen: set[str] = set()
            written = 0
            extracted_files: list[str] = []
            for member in members:
                target = _safe_archive_target(destination, member.filename)
                normalized = target.relative_to(destination).as_posix().casefold()
                if normalized in seen:
                    raise ReleaseError(f"Doppelter Pfad im Release-Archiv: {member.filename}")
                seen.add(normalized)
                mode = member.external_attr >> 16
                file_type = stat.S_IFMT(mode)
                if file_type == stat.S_IFLNK:
                    raise ReleaseError(f"Symbolische Links sind im Release-Archiv nicht zulässig: {member.filename}")
                if file_type not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise ReleaseError(f"Nicht unterstützter Dateityp im Release-Archiv: {member.filename}")
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if member.file_size > MAX_UNPACKED_BYTES:
                    raise ReleaseError(f"Datei im Release-Archiv ist zu groß: {member.filename}")
                target.parent.mkdir(parents=True, exist_ok=True)
                file_written = 0
                with archive.open(member, "r") as source, target.open("xb") as output:
                    while chunk := source.read(1024 * 1024):
                        file_written += len(chunk)
                        written += len(chunk)
                        if file_written > member.file_size or written > MAX_UNPACKED_BYTES:
                            raise ReleaseError("Das Archiv enthält unerwartet mehr Daten als angekündigt.")
                        output.write(chunk)
                if file_written != member.file_size:
                    raise ReleaseError(f"Unvollständige Datei im Release-Archiv: {member.filename}")
                extracted_files.append(target.relative_to(destination).as_posix())
                if progress:
                    progress(written, total_size)
        if not (destination / "Nexa.exe").is_file():
            raise ReleaseError("Das Release enthält keine Nexa.exe.")
        if not (destination / "NexaRuntime.ico").is_file():
            raise ReleaseError("Das Release enthält kein NexaRuntime.ico.")
        return extracted_files
    except (zipfile.BadZipFile, OSError) as error:
        shutil.rmtree(destination, ignore_errors=True)
        if isinstance(error, ReleaseError):
            raise
        raise ReleaseError(f"Das Release-Archiv konnte nicht sicher entpackt werden: {error}") from error
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise


def default_install_root() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise ReleaseError("LOCALAPPDATA ist nicht gesetzt; kein benutzerspezifischer Installationspfad verfügbar.")
    return Path(local_app_data) / "Programs" / "Nexa"


def _current_version_path(root: Path) -> Path:
    return root / "current-version.txt"


def read_installed_version(root: Path) -> str | None:
    try:
        version = _current_version_path(root).read_text(encoding="ascii").strip()
    except FileNotFoundError:
        return None
    if not VERSION_PATTERN.fullmatch(version):
        raise ReleaseError("Die installierte Versionsdatei ist ungültig.")
    executable = root / "versions" / version / "Nexa.exe"
    if not executable.is_file():
        raise ReleaseError(f"Die installierte Nexa-Version {version} ist unvollständig.")
    return version


def _launcher_contents() -> bytes:
    contents = (
        "@echo off\r\n"
        "setlocal\r\n"
        'set "NEXA_ROOT=%~dp0.."\r\n'
        'set /p "NEXA_VERSION="<"%NEXA_ROOT%\\current-version.txt"\r\n'
        'if not defined NEXA_VERSION (\r\n'
        '  echo Nexa ist nicht installiert oder die Version fehlt. 1>&2\r\n'
        "  exit /b 1\r\n"
        ")\r\n"
        'set "NEXA_EXE=%NEXA_ROOT%\\versions\\%NEXA_VERSION%\\Nexa.exe"\r\n'
        'if not exist "%NEXA_EXE%" (\r\n'
        '  echo Nexa-Version %NEXA_VERSION% wurde nicht gefunden. 1>&2\r\n'
        "  exit /b 1\r\n"
        ")\r\n"
        '"%NEXA_EXE%" %*\r\n'
        "exit /b %errorlevel%\r\n"
    )
    return contents.encode("ascii")


def _read_user_path() -> tuple[str, int]:
    if sys.platform != "win32":
        raise ReleaseError("Die Nexa-Installation und PATH-Einrichtung werden nur unter Windows unterstützt.")
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            "Environment",
            0,
            winreg.KEY_QUERY_VALUE,
        ) as key:
            value, value_type = winreg.QueryValueEx(key, "Path")
            return str(value), value_type
    except FileNotFoundError:
        return "", winreg.REG_EXPAND_SZ


def _write_user_path(value: str, value_type: int) -> None:
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        winreg.SetValueEx(key, "Path", 0, value_type, value)
    try:
        import ctypes

        ctypes.windll.user32.SendMessageTimeoutW(
            0xFFFF,
            0x001A,
            0,
            "Environment",
            0x0002,
            5000,
            None,
        )
    except (AttributeError, OSError):
        pass


def update_user_path(bin_directory: Path, add: bool) -> None:
    path_value, value_type = _read_user_path()
    updated = merge_user_path(path_value, bin_directory, add)
    if updated == path_value:
        return
    _write_user_path(updated, value_type)


def merge_user_path(path_value: str, bin_directory: Path, add: bool) -> str:
    entries = [entry for entry in path_value.split(os.pathsep) if entry]
    normalized_target = os.path.normcase(os.path.abspath(bin_directory))
    remaining = [
        entry for entry in entries
        if os.path.normcase(os.path.abspath(os.path.expandvars(entry.strip('"'))))
        != normalized_target
    ]
    updated = [str(bin_directory), *remaining] if add else remaining
    return os.pathsep.join(updated)


def install_verified_release(
    archive_path: Path,
    version: str,
    install_root: Path,
    path_updater: Callable[[Path, bool], None] = update_user_path,
    progress: Callable[[int, int], None] | None = None,
) -> Path:
    if not VERSION_PATTERN.fullmatch(version):
        raise ReleaseError(f"Ungültige Nexa-Version: {version}")
    root = install_root.expanduser().resolve()
    versions_root = root / "versions"
    bin_root = root / "bin"
    destination = versions_root / version
    staging = versions_root / f".staging-{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    if any(path.is_symlink() for path in (root / "versions", bin_root)):
        raise ReleaseError("Installationsordner darf keine Nexa-Systemordner über symbolische Links umlenken.")
    if destination.exists() or destination.is_symlink():
        raise ReleaseError(
            f"Nexa {version} ist bereits installiert. Wähle eine andere Version "
            "oder deinstalliere die Installation zuerst."
        )

    marker_path = root / "install.json"
    if marker_path.is_symlink() or _current_version_path(root).is_symlink():
        raise ReleaseError("Installationsmetadaten dürfen keine symbolischen Links sein.")
    previous_marker = marker_path.read_bytes() if marker_path.exists() else None
    if previous_marker is not None:
        try:
            marker = json.loads(previous_marker.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ReleaseError("Vorhandene Installationsmetadaten sind ungültig.") from error
        if marker.get("application_id") != APP_ID or Path(marker.get("install_root", "")).resolve() != root:
            raise ReleaseError("Der ausgewählte Ordner wird bereits von einer anderen Anwendung verwendet.")
        marker_versions = marker.get("versions", [])
        if not isinstance(marker_versions, list) or any(
            not isinstance(item, str) or not VERSION_PATTERN.fullmatch(item)
            for item in marker_versions
        ):
            raise ReleaseError("Installationsmetadaten enthalten ungültige Versionen.")
        installed_versions = set(marker_versions)
        owned_files = marker.get("owned_files", {})
        if not isinstance(owned_files, dict):
            raise ReleaseError("Installationsmetadaten enthalten ungültige Dateilisten.")
        for file_version, file_list in owned_files.items():
            if (
                not isinstance(file_version, str)
                or not VERSION_PATTERN.fullmatch(file_version)
                or not isinstance(file_list, list)
                or any(not isinstance(name, str) for name in file_list)
            ):
                raise ReleaseError("Installationsmetadaten enthalten ungültige Dateilisten.")
            for name in file_list:
                _safe_archive_target(Path("owned-files-root"), name)
    else:
        root_entries = list(root.iterdir())
        if root_entries and not (
            root_entries == [versions_root]
            and versions_root.is_dir()
            and not any(versions_root.iterdir())
        ):
            raise ReleaseError(
                "Der ausgewählte Installationsordner ist nicht leer und gehört keiner Nexa-Installation."
            )
        installed_versions = set()
        owned_files = {}

    versions_root.mkdir(parents=True, exist_ok=True)
    if bin_root.exists() and not (marker_path.exists() and (bin_root / "nexa.cmd").is_file()):
        raise ReleaseError("Der bin-Ordner enthält keine erkennbare Nexa-Installation.")
    launcher = bin_root / "nexa.cmd"
    if launcher.is_symlink():
        raise ReleaseError("Die vorhandene nexa.cmd ist ein symbolischer Link und wird nicht überschrieben.")
    if launcher.exists() and launcher.read_bytes() != _launcher_contents():
        raise ReleaseError("Die vorhandene nexa.cmd wurde verändert; sie wird nicht überschrieben.")

    previous_current = None
    current_path = _current_version_path(root)
    if current_path.exists():
        previous_current = current_path.read_bytes()

    try:
        extracted_files = extract_verified_package(archive_path, staging, progress)
        os.replace(staging, destination)
        bin_root.mkdir(parents=True, exist_ok=True)
        if not launcher.exists():
            launcher.write_bytes(_launcher_contents())
        installed_versions.add(version)
        marker = {
            "application_id": APP_ID,
            "install_root": str(root),
            "versions": sorted(installed_versions),
        }
        owned_files[version] = extracted_files
        marker["owned_files"] = owned_files
        _atomic_write(marker_path, json.dumps(marker, indent=2).encode("utf-8"))
        _atomic_write(current_path, f"{version}\n".encode("ascii"))
        path_updater(bin_root, True)
    except Exception as error:
        if previous_current is None:
            current_path.unlink(missing_ok=True)
        else:
            _atomic_write(current_path, previous_current)
        if previous_marker is None:
            marker_path.unlink(missing_ok=True)
        else:
            _atomic_write(marker_path, previous_marker)
        shutil.rmtree(destination, ignore_errors=True)
        if previous_marker is None:
            launcher.unlink(missing_ok=True)
            try:
                bin_root.rmdir()
            except OSError:
                pass
        if isinstance(error, ReleaseError):
            raise
        raise ReleaseError(f"Nexa {version} konnte nicht installiert werden: {error}") from error
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return destination


def activate_installed_version(
    version: str,
    install_root: Path,
    path_updater: Callable[[Path, bool], None] = update_user_path,
) -> Path:
    if not VERSION_PATTERN.fullmatch(version):
        raise ReleaseError(f"Ungültige Nexa-Version: {version}")
    root = install_root.expanduser().resolve()
    destination = root / "versions" / version
    marker_path = root / "install.json"
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseError(f"Keine gültige Nexa-Installation gefunden: {error}") from error
    if marker.get("application_id") != APP_ID or Path(marker.get("install_root", "")).resolve() != root:
        raise ReleaseError("Installationsmetadaten stimmen nicht mit diesem Ordner überein.")
    if version not in marker.get("versions", []) or not (destination / "Nexa.exe").is_file():
        raise ReleaseError(f"Nexa {version} ist in diesem Ordner nicht installiert.")

    current_path = _current_version_path(root)
    previous_current = current_path.read_bytes() if current_path.exists() else None
    try:
        _atomic_write(current_path, f"{version}\n".encode("ascii"))
        path_updater(root / "bin", True)
    except Exception as error:
        if previous_current is None:
            current_path.unlink(missing_ok=True)
        else:
            _atomic_write(current_path, previous_current)
        if isinstance(error, ReleaseError):
            raise
        raise ReleaseError(f"Nexa {version} konnte nicht aktiviert werden: {error}") from error
    return destination


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def uninstall_nexa(
    install_root: Path,
    path_updater: Callable[[Path, bool], None] = update_user_path,
) -> None:
    root = install_root.expanduser().resolve()
    marker_path = root / "install.json"
    if (
        marker_path.is_symlink()
        or _current_version_path(root).is_symlink()
        or (root / "versions").is_symlink()
        or (root / "bin").is_symlink()
    ):
        raise ReleaseError("Installationspfad enthält einen unerwarteten symbolischen Link.")
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseError(f"Keine gültige Nexa-Installation gefunden: {error}") from error
    if marker.get("application_id") != APP_ID or Path(marker.get("install_root", "")).resolve() != root:
        raise ReleaseError("Installationsmetadaten stimmen nicht mit diesem Ordner überein.")
    versions = marker.get("versions")
    if not isinstance(versions, list) or any(
        not isinstance(version, str) or not VERSION_PATTERN.fullmatch(version)
        for version in versions
    ):
        raise ReleaseError("Installationsmetadaten enthalten ungültige Versionen.")
    owned_files = marker.get("owned_files", {})
    if not isinstance(owned_files, dict):
        raise ReleaseError("Installationsmetadaten enthalten ungültige Dateilisten.")
    for version, file_list in owned_files.items():
        if (
            version not in versions
            or not isinstance(file_list, list)
            or any(not isinstance(name, str) for name in file_list)
        ):
            raise ReleaseError("Installationsmetadaten enthalten ungültige Dateilisten.")
        for name in file_list:
            _safe_archive_target(Path("owned-files-root"), name)

    bin_root = root / "bin"
    launcher = bin_root / "nexa.cmd"
    if launcher.is_symlink():
        raise ReleaseError("Die installierte nexa.cmd ist ein symbolischer Link.")
    path_updater(bin_root, False)
    if launcher.is_file() and launcher.read_bytes() == _launcher_contents():
        launcher.unlink()
    marker_path.unlink()
    _current_version_path(root).unlink(missing_ok=True)

    versions_root = root / "versions"
    for version in versions:
        version_root = versions_root / version
        if version_root.is_dir() and not version_root.is_symlink():
            for name in owned_files.get(version, []):
                owned_file = _safe_archive_target(version_root, name)
                if owned_file.is_file() or owned_file.is_symlink():
                    owned_file.unlink()
            for directory in sorted(
                (path for path in version_root.rglob("*") if path.is_dir() and not path.is_symlink()),
                key=lambda path: len(path.parts),
                reverse=True,
            ):
                try:
                    directory.rmdir()
                except OSError:
                    pass
            try:
                version_root.rmdir()
            except OSError:
                pass
    for directory in (bin_root, versions_root, root):
        try:
            directory.rmdir()
        except OSError:
            pass
