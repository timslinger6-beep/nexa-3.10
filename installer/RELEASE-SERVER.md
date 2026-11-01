# Nexa Installer und Release-Server

## Projektstand und Sicherheitsgrenzen

Der Installer baut die im Projekt vorhandene CLI-Version automatisch aus
`main.py` (im aktuellen Arbeitsstand: Nexa 3.20.0). Die Anwendung wird als
PyInstaller-`onedir`-Paket ausgeliefert. Python, Tkinter und die von Nexa
verwendeten Standardbibliotheken werden in diesem Ordner mitgeliefert. Auf dem
Ziel-PC muss Python weder installiert noch im `PATH` sein.

Der Installer lädt ausschließlich:

1. `manifest.json`,
2. `manifest.json.sig`,
3. das im verifizierten Manifest ausgewählte Windows-x64-ZIP.

Die Signatur ist Ed25519; der SHA-256-Hash und die exakte Paketgröße sind im
signierten Manifest enthalten. Ein Hash ohne Signatur wäre kein ausreichender
Schutz, wenn Manifest und Paket vom selben Server kommen. Der private
Signaturschlüssel gehört deshalb ausschließlich in einen geschützten
Release-Prozess und niemals ins Repository oder in die Installer-EXE.

Der Nexa-Quellcode bleibt öffentlich. Die EXE bündelt den Interpreter für eine
einfache Installation; sie macht den öffentlichen Quellcode nicht geheim und
verhindert keine Analyse der Anwendung.

## Signing-Key einmalig erzeugen

Zuerst den Installer-Build einmal ausführen, damit die lokale Build-Umgebung
und `cryptography` vorhanden sind. Erzeuge den privaten Schlüssel danach an
einem geschützten Ort außerhalb des Repositorys und sichere eine
verschlüsselte Offline-Kopie. Beispiel für den Build-Rechner:

```powershell
.\.venv-nexa-installer\Scripts\python.exe -c 'from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey; from cryptography.hazmat.primitives import serialization; from pathlib import Path; p=Path.home() / "NexaReleaseSigningKey.pem"; k=Ed25519PrivateKey.generate(); p.write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())); print(p)'
```

Diese Beispielschlüsseldatei ist unverschlüsselt. Beschränke auf Windows ihre
ACL auf das Release-Konto, lege sie nicht in Git/Cloud-Sync ab und verwende für
den eigentlichen Produktionsbetrieb ein passendes Secret-/HSM-Verfahren.
Das Erzeugen eines Schlüssels ist eine einmalige Release-Verantwortung; bei
Verlust muss ein neuer öffentlicher Schlüssel in einen neu gebauten Installer.

## Dateien auf dem HTTPS-Server

Lege die folgenden Dateien unter derselben HTTPS-Origin ab:

```text
/nexa/stable/manifest.json
/nexa/stable/manifest.json.sig
/nexa/stable/packages/nexa-3.20.0-windows-x64.zip
```

Der signierte Manifest-Inhalt ist UTF-8-JSON mit Schema 1:

```json
{
  "schema": 1,
  "latest": "3.20.0",
  "releases": [
    {
      "version": "3.20.0",
      "platform": "windows-x64",
      "package_url": "https://updates.example.org/nexa/stable/packages/nexa-3.20.0-windows-x64.zip",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
      "size": 123456789,
      "min_installer": "1.0.0"
    }
  ]
}
```

`manifest.json.sig` enthält die Base64-kodierte Ed25519-Signatur der **exakten
Bytes** von `manifest.json`, gefolgt von einem Zeilenumbruch. `package_url`
muss HTTPS und dieselbe Host-Origin wie das Manifest verwenden. Das ZIP muss
`Nexa.exe` und `NexaRuntime.ico` im Stamm enthalten; der PyInstaller-Build
packt zusätzlich die nötigen Laufzeitdateien und Abhängigkeiten ein.

Der Server benötigt keine ausführbaren Skripte. Stelle nur statische Dateien
über HTTPS bereit; verwende gültige TLS-Zertifikate und keine Redirects auf
andere Hosts. Der Installer akzeptiert keine HTTP-URLs, fremden Redirects,
fremde Package-Origins, ungültige Signaturen, falschen Paket-Hash, falsche
Größe, unsichere ZIP-Pfade oder symbolischen Links.

## Build und Veröffentlichung

Für einen normalen lokalen Build:

```powershell
.\installer\build-installer.ps1
```

Für einen signierten Release-Build (URLs an den eigenen Server anpassen):

```powershell
.\installer\build-installer.ps1 `
  -ManifestUrl "https://updates.example.org/nexa/stable/manifest.json" `
  -PackageBaseUrl "https://updates.example.org/nexa/stable/packages/" `
  -SigningKeyPath "$env:USERPROFILE\NexaReleaseSigningKey.pem"
```

Dieser Build erzeugt eine EXE mit dem dazu passenden eingebetteten
öffentlichen Schlüssel. Das Release-Paket sowie das signierte Manifest liegen
danach in `build\NexaInstallerRelease\release`. Lade nur diese drei
Release-Dateien auf den HTTPS-Server. Die normale Installation bezieht keine
`.py`-Dateien und führt keine heruntergeladenen Skripte aus.

Bei späteren Releases müssen frühere Pakete/Manifest-Einträge erhalten
bleiben, wenn Nutzer sie im Installer auswählen oder auf sie zurückschalten
sollen. Lade vor dem Release-Build `manifest.json` und `manifest.json.sig` vom
Server in einen geschützten temporären Ordner und übergib beide Dateien:

```powershell
.\installer\build-installer.ps1 `
  -ManifestUrl "https://updates.example.org/nexa/stable/manifest.json" `
  -PackageBaseUrl "https://updates.example.org/nexa/stable/packages/" `
  -SigningKeyPath "$env:USERPROFILE\NexaReleaseSigningKey.pem" `
  -PreviousManifestPath "$env:TEMP\nexa-release\manifest.json" `
  -PreviousSignaturePath "$env:TEMP\nexa-release\manifest.json.sig"
```

Der Build verifiziert das vorherige Manifest mit dem Signaturschlüssel, bevor
er dessen Release-Versionen übernimmt. Bei einer Schlüsselrotation müssen
bestehende Nutzer weiterhin einen Installer mit dem bisherigen öffentlichen
Schlüssel erhalten oder bewusst eine neue Vertrauenskette einrichten.

`installer/release-config.json` enthält den Build-Standard. Ohne eigene
Konfiguration zeigt er absichtlich auf `example.invalid` und hat keinen
öffentlichen Schlüssel; der resultierende Installer kann daher noch keine
Release-Informationen abrufen. Eine echte Server-URL und ein korrekt
abgeleiteter öffentlicher Ed25519-Schlüssel werden für die Veröffentlichung
benötigt. Das Build-Skript verändert die Quellkonfiguration nicht.

## Installationsverhalten

- Standardziel ist `%LOCALAPPDATA%\Programs\Nexa`; kein Administratorrecht.
- Nexa-Versionen werden getrennt gespeichert. Ein Update wechselt erst nach
  erfolgreicher Verifikation und Installation atomar die aktive Version.
- `bin\nexa.cmd` liest die aktive Version ein und reicht Argumente an
  `Nexa.exe` weiter. `nexa --version`, `nexa help` und `nexa run datei.nexa`
  verwenden die echte vorhandene CLI.
- Der Installer ergänzt ausschließlich seinen benutzerspezifischen `bin`-
  Ordner im HKCU-PATH. Bereits geöffnete Terminals übernehmen PATH-Änderungen
  nicht; danach ein neues PowerShell-Fenster öffnen.
- Die Deinstallation entfernt Nexa-Programmdateien unter dem Installationsziel
  und den zugehörigen PATH-Eintrag. Persönliche Projekte außerhalb dieses
  Programmordners bleiben unangetastet.

## Tests und Grenzen

Die lokalen Installer-Tests laufen mit:

```powershell
.\.venv-nexa-installer\Scripts\python.exe -m unittest -v installer.test_installer_core
```

Ein erfolgreicher lokaler Build beweist weder die Funktion des noch nicht
konfigurierten Release-Servers noch die Ausführung auf einem sauberen
Windows-11-Rechner ohne Python. Diese Prüfungen müssen nach Einrichtung des
HTTPS-Servers auf einer frischen VM durchgeführt werden. Für eine vertrauens-
würdige öffentliche Verteilung ist zusätzlich Code-Signing der EXE mit einem
Windows-Code-Signing-Zertifikat empfehlenswert; es ist nicht im Projekt
vorhanden.
