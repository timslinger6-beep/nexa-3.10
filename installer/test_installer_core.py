from __future__ import annotations

import base64
import hashlib
import json
import tempfile
import unittest
import zipfile
from argparse import Namespace
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from installer.installer_core import (
    APP_ID,
    ReleaseError,
    activate_installed_version,
    extract_verified_package,
    install_verified_release,
    read_installed_version,
    uninstall_nexa,
    verify_manifest,
)
from installer.release_tools import package_command


def create_package(path: Path, executable: bytes = b"nexa") -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Nexa.exe", executable)
        archive.writestr("NexaRuntime.ico", b"icon")
        archive.writestr("_internal/python313.dll", b"runtime")
    return path


class InstallerCoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_valid_manifest_signature_and_tamper_detection(self):
        private_key = Ed25519PrivateKey.generate()
        public_key = base64.b64encode(
            private_key.public_key().public_bytes(
                serialization.Encoding.Raw,
                serialization.PublicFormat.Raw,
            )
        ).decode("ascii")
        manifest = {
            "schema": 1,
            "latest": "3.1.0",
            "releases": [
                {
                    "version": "3.1.0",
                    "platform": "windows-x64",
                    "package_url": "https://updates.example.test/nexa.zip",
                    "sha256": hashlib.sha256(b"package").hexdigest(),
                    "size": 7,
                    "min_installer": "1.0.0",
                }
            ],
        }
        manifest_bytes = json.dumps(manifest, separators=(",", ":")).encode()
        signature = base64.b64encode(private_key.sign(manifest_bytes))

        verified = verify_manifest(manifest_bytes, signature, public_key)
        self.assertEqual(verified["latest"], "3.1.0")
        with self.assertRaisesRegex(ReleaseError, "Signatur"):
            verify_manifest(manifest_bytes + b" ", signature, public_key)

    def test_rejects_manifest_with_duplicate_keys(self):
        private_key = Ed25519PrivateKey.generate()
        public_key = base64.b64encode(
            private_key.public_key().public_bytes(
                serialization.Encoding.Raw,
                serialization.PublicFormat.Raw,
            )
        ).decode("ascii")
        manifest_bytes = (
            b'{"schema":1,"schema":1,"latest":"3.1.0","releases":[]}'
        )
        signature = base64.b64encode(private_key.sign(manifest_bytes))

        with self.assertRaisesRegex(ReleaseError, "Doppelter JSON-Schlüssel"):
            verify_manifest(manifest_bytes, signature, public_key)

    def test_rejects_unsigned_or_unsafe_archive_paths(self):
        archive_path = self.root / "unsafe.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("../outside.txt", "bad")
        destination = self.root / "stage"

        with self.assertRaisesRegex(ReleaseError, "Unsicherer Pfad"):
            extract_verified_package(archive_path, destination)
        self.assertFalse((self.root / "outside.txt").exists())
        self.assertFalse(destination.exists())

    def test_rejects_symlink_in_archive(self):
        archive_path = self.root / "symlink.zip"
        entry = zipfile.ZipInfo("Nexa.exe")
        entry.external_attr = (0o120777 << 16)
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr(entry, "outside.exe")
        destination = self.root / "stage"

        with self.assertRaisesRegex(ReleaseError, "(?i)symbolische Links"):
            extract_verified_package(archive_path, destination)
        self.assertFalse(destination.exists())

    def test_install_and_switch_between_verified_versions(self):
        archive_path = create_package(self.root / "nexa.zip")
        install_root = self.root / "programs" / "Nexa"
        path_updates = []

        def update_path(directory: Path, add: bool):
            path_updates.append((directory, add))

        install_verified_release(
            archive_path, "3.1.0", install_root, path_updater=update_path
        )
        self.assertEqual(read_installed_version(install_root), "3.1.0")

        archive_v2 = create_package(self.root / "nexa-v2.zip", b"nexa-v2")
        install_verified_release(
            archive_v2, "3.2.0", install_root, path_updater=update_path
        )
        self.assertEqual(read_installed_version(install_root), "3.2.0")

        activate_installed_version(
            "3.1.0", install_root, path_updater=update_path
        )
        self.assertEqual(read_installed_version(install_root), "3.1.0")
        self.assertTrue((install_root / "versions" / "3.2.0" / "Nexa.exe").exists())
        self.assertEqual(len(path_updates), 3)

    def test_install_accepts_empty_versions_directory_from_interrupted_setup(self):
        archive_path = create_package(self.root / "nexa.zip")
        install_root = self.root / "programs" / "Nexa"
        (install_root / "versions").mkdir(parents=True)

        install_verified_release(
            archive_path,
            "3.1.0",
            install_root,
            path_updater=lambda directory, add: None,
        )

        self.assertTrue((install_root / "versions" / "3.1.0" / "Nexa.exe").is_file())

    def test_failed_update_preserves_active_version_and_metadata(self):
        archive_path = create_package(self.root / "nexa.zip")
        install_root = self.root / "programs" / "Nexa"
        install_verified_release(
            archive_path,
            "3.1.0",
            install_root,
            path_updater=lambda directory, add: None,
        )
        previous_metadata = (install_root / "install.json").read_bytes()
        archive_v2 = create_package(self.root / "nexa-v2.zip", b"nexa-v2")

        def fail_path_update(directory: Path, add: bool):
            raise OSError("simulierter Registry-Fehler")

        with self.assertRaisesRegex(ReleaseError, "konnte nicht installiert werden"):
            install_verified_release(
                archive_v2,
                "3.2.0",
                install_root,
                path_updater=fail_path_update,
            )

        self.assertEqual(read_installed_version(install_root), "3.1.0")
        self.assertEqual((install_root / "install.json").read_bytes(), previous_metadata)
        self.assertFalse((install_root / "versions" / "3.2.0").exists())

    def test_uninstall_preserves_files_outside_install_root(self):
        archive_path = create_package(self.root / "nexa.zip")
        install_root = self.root / "programs" / "Nexa"
        project_file = self.root / "my-project" / "main.nexa"
        project_file.parent.mkdir()
        project_file.write_text('print("keep");', encoding="utf-8")
        path_updates = []

        install_verified_release(
            archive_path,
            "3.1.0",
            install_root,
            path_updater=lambda directory, add: path_updates.append((directory, add)),
        )
        marker = json.loads((install_root / "install.json").read_text(encoding="utf-8"))
        self.assertEqual(marker["application_id"], APP_ID)

        uninstall_nexa(
            install_root,
            path_updater=lambda directory, add: path_updates.append((directory, add)),
        )
        self.assertTrue(project_file.exists())
        self.assertEqual(path_updates[-1][1], False)
        self.assertFalse((install_root / "versions" / "3.1.0").exists())

    def test_release_tool_signs_package_and_preserves_previous_releases(self):
        private_key_path = self.root / "release-key.pem"
        private_key = Ed25519PrivateKey.generate()
        private_key_path.write_bytes(
            private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        app_directory = self.root / "application"
        app_directory.mkdir()
        (app_directory / "Nexa.exe").write_bytes(b"application")
        internal_directory = app_directory / "_internal"
        internal_directory.mkdir()
        (internal_directory / "NexaRuntime.ico").write_bytes(b"icon")
        output_directory = self.root / "release"
        common = {
            "app_directory": app_directory,
            "output_directory": output_directory,
            "manifest_url": "https://updates.example.test/nexa/stable/manifest.json",
            "package_base_url": "https://updates.example.test/nexa/stable/packages/",
            "signing_key": private_key_path,
        }

        package_command(Namespace(**common, version="3.0.9", previous_manifest=None, previous_signature=None))
        previous_manifest = output_directory / "manifest.json"
        previous_signature = output_directory / "manifest.json.sig"
        with zipfile.ZipFile(output_directory / "nexa-3.0.9-windows-x64.zip") as archive:
            self.assertEqual(archive.read("NexaRuntime.ico"), b"icon")
        package_command(
            Namespace(
                **common,
                version="3.1.0",
                previous_manifest=previous_manifest,
                previous_signature=previous_signature,
            )
        )
        public_key = base64.b64encode(
            private_key.public_key().public_bytes(
                serialization.Encoding.Raw,
                serialization.PublicFormat.Raw,
            )
        ).decode("ascii")
        verified = verify_manifest(
            previous_manifest.read_bytes(),
            previous_signature.read_bytes(),
            public_key,
        )

        self.assertEqual(verified["latest"], "3.1.0")
        self.assertEqual(
            [release["version"] for release in verified["releases"]],
            ["3.1.0", "3.0.9"],
        )

    def test_uninstall_preserves_unowned_files_in_program_directory(self):
        archive_path = create_package(self.root / "nexa.zip")
        install_root = self.root / "programs" / "Nexa"
        install_verified_release(
            archive_path,
            "3.1.0",
            install_root,
            path_updater=lambda directory, add: None,
        )
        personal_file = (
            install_root / "versions" / "3.1.0" / "my-notes.txt"
        )
        personal_file.write_text("keep this user data", encoding="utf-8")

        uninstall_nexa(install_root, path_updater=lambda directory, add: None)

        self.assertEqual(personal_file.read_text(encoding="utf-8"), "keep this user data")
        self.assertFalse(
            (install_root / "versions" / "3.1.0" / "Nexa.exe").exists()
        )


if __name__ == "__main__":
    unittest.main()
