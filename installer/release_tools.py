from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from urllib.parse import urljoin, urlsplit

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from installer.installer_core import verify_manifest


def load_signing_key(path: Path) -> Ed25519PrivateKey:
    try:
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    except (OSError, ValueError, TypeError) as error:
        raise SystemExit(f"Signing key could not be loaded: {error}") from error
    if not isinstance(key, Ed25519PrivateKey):
        raise SystemExit("The release signing key must be Ed25519 PEM.")
    return key


def public_key_command(args: argparse.Namespace) -> None:
    key = load_signing_key(args.key)
    public_bytes = key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    print(base64.b64encode(public_bytes).decode("ascii"))


def project_version_command(args: argparse.Namespace) -> None:
    tree = ast.parse(args.main_file.read_text(encoding="utf-8-sig"))
    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        if any(
            isinstance(target, ast.Name) and target.id == "VERSION"
            for target in statement.targets
        ):
            version = ast.literal_eval(statement.value)
            if not isinstance(version, str):
                break
            print(version)
            return
    raise SystemExit(f"VERSION wurde nicht gefunden in {args.main_file}")


def canonical_json(value: dict) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def is_private_or_local_host(host: str | None) -> bool:
    if not host:
        return False
    host = host.lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        import ipaddress
        address = ipaddress.ip_address(host)
        return address.is_private or address.is_loopback or address.is_link_local
    except ValueError:
        return False


def require_https(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme == "https" and parsed.hostname:
        if parsed.username or parsed.password or parsed.fragment:
            raise SystemExit("URLs containing credentials or fragments are not allowed.")
        return
    if parsed.scheme == "http" and parsed.hostname and is_private_or_local_host(parsed.hostname):
        if parsed.username or parsed.password or parsed.fragment:
            raise SystemExit("URLs containing credentials or fragments are not allowed.")
        return
    raise SystemExit("Manifest and package URLs must use HTTPS or a private/local HTTP URL.")


def package_command(args: argparse.Namespace) -> None:
    app_directory = args.app_directory.resolve()
    output_directory = args.output_directory.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    version = args.version
    if not version or any(character not in "0123456789." for character in version):
        raise SystemExit("Version must be a numeric semantic version such as 3.1.0.")
    require_https(args.manifest_url)
    require_https(args.package_base_url)

    package_name = f"nexa-{version}-windows-x64.zip"
    package_path = output_directory / package_name
    files = sorted(path for path in app_directory.rglob("*") if path.is_file())
    if not any(path.name == "Nexa.exe" for path in files):
        raise SystemExit(f"Nexa.exe was not found in {app_directory}")
    if not any(path.name == "NexaRuntime.ico" for path in files):
        raise SystemExit(f"NexaRuntime.ico was not found in {app_directory}")
    root_icon = app_directory / "NexaRuntime.ico"
    nested_icon = next(
        (path for path in files if path.name == "NexaRuntime.ico"),
        None,
    )
    for path in files:
        if path.is_symlink():
            raise SystemExit(f"Symlinks are not permitted in a release package: {path}")

    with zipfile.ZipFile(
        package_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as archive:
        for path in files:
            archive.write(path, path.relative_to(app_directory).as_posix())
        if not root_icon.is_file() and nested_icon is not None:
            archive.write(nested_icon, "NexaRuntime.ico")

    digest = hashlib.sha256()
    size = 0
    with package_path.open("rb") as package:
        while chunk := package.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)

    package_url = urljoin(args.package_base_url.rstrip("/") + "/", package_name)
    manifest_origin = urlsplit(args.manifest_url)
    package_origin = urlsplit(package_url)
    if (manifest_origin.hostname, manifest_origin.port or 443) != (
        package_origin.hostname,
        package_origin.port or 443,
    ):
        raise SystemExit("Manifest and package must use the same HTTPS server.")
    releases = []
    if bool(args.previous_manifest) != bool(args.previous_signature):
        raise SystemExit(
            "Both --previous-manifest and --previous-signature must be supplied together."
        )
    signing_key = load_signing_key(args.signing_key)
    if args.previous_manifest:
        try:
            previous_bytes = args.previous_manifest.read_bytes()
            previous_manifest = verify_manifest(
                previous_bytes,
                args.previous_signature.read_bytes(),
                base64.b64encode(
                    signing_key.public_key().public_bytes(
                        serialization.Encoding.Raw,
                        serialization.PublicFormat.Raw,
                    )
                ).decode("ascii"),
            )
        except Exception as error:
            raise SystemExit(f"The previous signed manifest could not be verified: {error}") from error
        for release in previous_manifest["releases"]:
            if (
                not isinstance(release, dict)
                or not isinstance(release.get("version"), str)
                or release["version"] == version
                or release.get("platform") != "windows-x64"
            ):
                raise SystemExit("The previous manifest contains an invalid or duplicate release.")
            previous_origin = urlsplit(release["package_url"])
            if (previous_origin.hostname, previous_origin.port or 443) != (
                manifest_origin.hostname,
                manifest_origin.port or 443,
            ):
                raise SystemExit("A previous release points to a different server.")
            releases.append(release)
    releases.append(
        {
            "version": version,
            "platform": "windows-x64",
            "package_url": package_url,
            "sha256": digest.hexdigest(),
            "size": size,
            "min_installer": "1.0.0",
        }
    )
    releases.sort(
        key=lambda release: tuple(int(part) for part in release["version"].split(".")),
        reverse=True,
    )
    manifest = {
        "schema": 1,
        "latest": version,
        "releases": releases,
    }
    manifest_bytes = canonical_json(manifest)
    signature = signing_key.sign(manifest_bytes)
    (output_directory / "manifest.json").write_bytes(manifest_bytes)
    (output_directory / "manifest.json.sig").write_bytes(
        base64.b64encode(signature) + b"\n"
    )
    print(f"Package:  {package_path}")
    print(f"SHA-256:  {digest.hexdigest()}")
    print(f"Manifest: {output_directory / 'manifest.json'}")
    print(f"Signature:{output_directory / 'manifest.json.sig'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and sign Nexa releases.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    public_key = subparsers.add_parser("public-key")
    public_key.add_argument("--key", type=Path, required=True)
    public_key.set_defaults(function=public_key_command)

    project_version = subparsers.add_parser("project-version")
    project_version.add_argument("--main-file", type=Path, required=True)
    project_version.set_defaults(function=project_version_command)

    package = subparsers.add_parser("package")
    package.add_argument("--app-directory", type=Path, required=True)
    package.add_argument("--output-directory", type=Path, required=True)
    package.add_argument("--version", required=True)
    package.add_argument("--manifest-url", required=True)
    package.add_argument("--package-base-url", required=True)
    package.add_argument("--signing-key", type=Path, required=True)
    package.add_argument("--previous-manifest", type=Path)
    package.add_argument("--previous-signature", type=Path)
    package.set_defaults(function=package_command)

    args = parser.parse_args()
    args.function(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
