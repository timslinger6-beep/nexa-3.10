from __future__ import annotations

import os
import queue
import sys
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

if getattr(sys, "frozen", False):
    BUNDLE_ROOT = Path(sys._MEIPASS)
    CONFIG_PATH = BUNDLE_ROOT / "release-config.json"
    ICON_PATH = BUNDLE_ROOT / "NexaRuntime.ico"
else:
    BUNDLE_ROOT = Path(__file__).resolve().parent.parent
    CONFIG_PATH = Path(__file__).resolve().with_name("release-config.json")
    ICON_PATH = BUNDLE_ROOT / "NexaRuntime.ico"

if str(BUNDLE_ROOT) not in sys.path:
    sys.path.insert(0, str(BUNDLE_ROOT))

from installer.installer_core import (  # noqa: E402
    INSTALLER_VERSION,
    ReleaseError,
    activate_installed_version,
    default_install_root,
    download_package,
    fetch_manifest,
    install_verified_release,
    load_config,
    read_installed_version,
    uninstall_nexa,
)


class NexaInstallerWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.events: queue.Queue[tuple] = queue.Queue()
        self.config = None
        self.manifest = None
        self.busy = False
        self.root.title(f"Nexa Installer {INSTALLER_VERSION}")
        self.root.geometry("700x530")
        self.root.minsize(650, 480)
        self.root.configure(padx=24, pady=18)
        if ICON_PATH.is_file():
            try:
                self.root.iconbitmap(str(ICON_PATH))
            except tk.TclError:
                pass
        self._build_ui()
        self._show_installed_version()
        self._set_status("Release-Informationen werden geprüft …")
        self._start_worker(self._check_worker)
        self.root.after(100, self._drain_events)

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root)
        header.pack(fill="x", pady=(0, 18))
        ttk.Label(header, text="Nexa", font=("Segoe UI", 24, "bold")).pack(anchor="w")
        ttk.Label(
            header,
            text="Installer und Update-Assistent · benötigt kein installiertes Python",
        ).pack(anchor="w", pady=(2, 0))

        self.installed_label = ttk.Label(self.root, text="Installierte Version: wird geprüft")
        self.installed_label.pack(anchor="w")
        self.available_label = ttk.Label(self.root, text="Verfügbare Version: noch nicht geprüft")
        self.available_label.pack(anchor="w", pady=(4, 14))

        path_frame = ttk.LabelFrame(self.root, text="Installationsordner", padding=10)
        path_frame.pack(fill="x", pady=(0, 14))
        self.path_value = tk.StringVar(value=str(default_install_root()))
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_value)
        self.path_entry.pack(side="left", fill="x", expand=True)
        self.browse_button = ttk.Button(path_frame, text="Durchsuchen …", command=self._browse)
        self.browse_button.pack(side="left", padx=(8, 0))

        release_frame = ttk.LabelFrame(self.root, text="Signiertes Release", padding=10)
        release_frame.pack(fill="x", pady=(0, 14))
        self.version_value = tk.StringVar()
        self.version_picker = ttk.Combobox(
            release_frame,
            textvariable=self.version_value,
            state="readonly",
            values=(),
        )
        self.version_picker.pack(fill="x")
        self.release_url_label = ttk.Label(
            release_frame,
            text=f"Manifest: {self._configured_manifest_url()}",
            wraplength=620,
        )
        self.release_url_label.pack(anchor="w", pady=(8, 0))

        self.status_value = tk.StringVar(value="Bereit")
        ttk.Label(self.root, textvariable=self.status_value, wraplength=640).pack(
            anchor="w", fill="x", pady=(4, 8)
        )
        self.progress = ttk.Progressbar(self.root, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(0, 14))

        buttons = ttk.Frame(self.root)
        buttons.pack(fill="x", side="bottom")
        self.check_button = ttk.Button(
            buttons, text="Updates suchen", command=self._check_for_updates
        )
        self.check_button.pack(side="left")
        self.install_button = ttk.Button(
            buttons, text="Installieren / Aktualisieren", command=self._install
        )
        self.install_button.pack(side="left", padx=8)
        self.uninstall_button = ttk.Button(
            buttons, text="Deinstallieren", command=self._uninstall
        )
        self.uninstall_button.pack(side="left")
        ttk.Button(buttons, text="Schließen", command=self.root.destroy).pack(side="right")

        self.footer = ttk.Label(
            self.root,
            text="Der Nexa-Quellcode bleibt öffentlich. Updates werden vor dem Entpacken "
            "mit Ed25519-Signatur und SHA-256 geprüft.",
            wraplength=640,
        )
        self.footer.pack(anchor="w", side="bottom", pady=(12, 10))

    def _configured_manifest_url(self) -> str:
        try:
            import json

            config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return str(config.get("manifest_url", "nicht konfiguriert"))
        except (OSError, ValueError):
            return "nicht konfiguriert"

    def _show_installed_version(self) -> None:
        try:
            version = read_installed_version(Path(self.path_value.get()))
        except (OSError, ReleaseError) as error:
            self.installed_label.configure(text=f"Installierte Version: Installationsstatus fehlerhaft ({error})")
            return
        self.installed_label.configure(
            text=f"Installierte Version: {version or 'keine'}"
        )

    def _set_status(self, message: str) -> None:
        self.status_value.set(message)

    def _browse(self) -> None:
        selected = filedialog.askdirectory(
            title="Nexa-Installationsordner auswählen",
            initialdir=self.path_value.get(),
            mustexist=False,
        )
        if selected:
            self.path_value.set(selected)
            self._show_installed_version()

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        for widget in (
            self.browse_button,
            self.path_entry,
            self.check_button,
            self.install_button,
            self.uninstall_button,
        ):
            widget.configure(state=state)
        if not busy:
            self.version_picker.configure(
                state="readonly" if self.version_picker["values"] else "disabled"
            )

    def _start_worker(self, worker: Callable[[], None]) -> None:
        if self.busy:
            return
        self._set_busy(True)
        threading.Thread(target=worker, daemon=True).start()

    def _check_worker(self) -> None:
        try:
            config = load_config(CONFIG_PATH)
            manifest = fetch_manifest(config)
            self.events.put(("manifest", config, manifest))
        except Exception as error:
            self.events.put(("error", str(error)))
        finally:
            self.events.put(("busy", False))

    def _check_for_updates(self) -> None:
        self.manifest = None
        self._set_status("Signatur und Release-Manifest werden über HTTPS geprüft …")
        self._start_worker(self._check_worker)

    def _install(self) -> None:
        if self.manifest is None:
            self._set_status("Bitte zuerst ein signiertes Release prüfen.")
            return
        selected = self.version_value.get()
        releases = {
            release["version"]: release for release in self.manifest["releases"]
        }
        release = releases.get(selected)
        if release is None:
            self._set_status("Bitte eine verfügbare Nexa-Version auswählen.")
            return
        install_root = Path(self.path_value.get().strip())
        if not self.path_value.get().strip():
            self._set_status("Bitte einen Installationsordner auswählen.")
            return
        if not messagebox.askyesno(
            "Nexa installieren",
            f"Nexa {selected} wird geprüft und installiert in:\n\n{install_root}\n\n"
            "Ältere installierte Versionen bleiben für einen Rollback erhalten.",
        ):
            return
        if (install_root / "versions" / selected / "Nexa.exe").is_file():
            self._set_status(f"Nexa {selected} wird als aktive Version gesetzt …")
            self._start_worker(
                lambda: self._activate_worker(selected, install_root)
            )
            return
        self._set_status(f"Nexa {selected} wird sicher heruntergeladen …")
        self.progress.configure(value=0, maximum=release["size"])
        self._start_worker(
            lambda: self._install_worker(release, install_root)
        )

    def _install_worker(self, release: dict, install_root: Path) -> None:
        try:
            with tempfile.TemporaryDirectory(prefix="nexa-installer-") as temporary:
                archive_path = Path(temporary) / "nexa-release.zip"

                def download_progress(current: int, total: int) -> None:
                    self.events.put(("progress", current, total, "Release wird geladen"))

                download_package(release, archive_path, download_progress)
                self.events.put(("status", "Signiertes Paket wird sicher entpackt …"))

                def extract_progress(current: int, total: int) -> None:
                    self.events.put(("progress", current, total, "Release wird entpackt"))

                installed = install_verified_release(
                    archive_path,
                    release["version"],
                    install_root,
                    progress=extract_progress,
                )
            self.events.put(("installed", release["version"], installed))
        except Exception as error:
            self.events.put(("error", str(error)))
        finally:
            self.events.put(("busy", False))

    def _activate_worker(self, version: str, install_root: Path) -> None:
        try:
            destination = activate_installed_version(version, install_root)
            self.events.put(("activated", version, destination))
        except Exception as error:
            self.events.put(("error", str(error)))
        finally:
            self.events.put(("busy", False))

    def _uninstall(self) -> None:
        root = Path(self.path_value.get())
        try:
            version = read_installed_version(root)
        except (OSError, ReleaseError) as error:
            self._set_status(str(error))
            return
        if version is None:
            self._set_status("In diesem Ordner ist Nexa nicht installiert.")
            return
        if not messagebox.askyesno(
            "Nexa deinstallieren",
            f"Nexa aus {root} entfernen?\n\n"
            "Persönliche Nexa-Projekte und Daten außerhalb dieses Installationsordners "
            "werden nicht gelöscht.",
        ):
            return
        self._set_status("Nexa wird deinstalliert …")
        self._start_worker(lambda: self._uninstall_worker(root))

    def _uninstall_worker(self, root: Path) -> None:
        try:
            uninstall_nexa(root)
            self.events.put(("uninstalled",))
        except Exception as error:
            self.events.put(("error", str(error)))
        finally:
            self.events.put(("busy", False))

    def _drain_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "manifest":
                    _, self.config, self.manifest = event
                    releases = self.manifest["releases"]
                    versions = [release["version"] for release in releases]
                    self.version_picker.configure(values=versions, state="readonly")
                    self.version_value.set(self.manifest["latest"])
                    self.available_label.configure(
                        text=f"Verfügbare Version: {self.manifest['latest']} "
                        f"({len(releases)} signierte Version(en))"
                    )
                    self._set_status("Manifest-Signatur gültig; Version und Pakethashes geprüft.")
                elif kind == "progress":
                    _, current, total, status = event
                    self.progress.configure(maximum=max(total, 1), value=current)
                    self._set_status(f"{status}: {current:,} / {total:,} Bytes")
                elif kind == "status":
                    self._set_status(event[1])
                elif kind == "installed":
                    _, version, destination = event
                    self.progress.configure(value=self.progress["maximum"])
                    self._show_installed_version()
                    self._set_status(
                        f"Nexa {version} erfolgreich installiert. "
                        "Öffne ein neues PowerShell-Fenster, um `nexa` zu verwenden."
                    )
                    messagebox.showinfo(
                        "Installation erfolgreich",
                        f"Nexa {version} wurde installiert.\n\n"
                        f"Programm: {destination}\n"
                        f"Befehl: {destination.parents[1] / 'bin' / 'nexa.cmd'}",
                    )
                elif kind == "activated":
                    _, version, destination = event
                    self._show_installed_version()
                    self._set_status(
                        f"Nexa {version} ist jetzt aktiv. Die vorherige Version bleibt erhalten."
                    )
                    messagebox.showinfo(
                        "Version gewechselt",
                        f"Nexa {version} wird jetzt verwendet.\n\n{destination}",
                    )
                elif kind == "uninstalled":
                    self._show_installed_version()
                    self._set_status(
                        "Nexa wurde entfernt. Persönliche Projekte wurden nicht angerührt."
                    )
                elif kind == "error":
                    self._set_status(f"Fehler: {event[1]}")
                    messagebox.showerror("Nexa Installer", event[1])
                elif kind == "busy":
                    self._set_busy(event[1])
        except queue.Empty:
            pass
        self.root.after(100, self._drain_events)


def main() -> int:
    if sys.platform != "win32":
        print("NexaInstaller.exe kann nur unter Windows ausgeführt werden.", file=sys.stderr)
        return 1
    if sys.maxsize <= 2**32:
        messagebox.showerror(
            "Nicht unterstützte Plattform",
            "Dieser Installer benötigt Windows x64.",
        )
        return 1
    root = tk.Tk()
    NexaInstallerWindow(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
