[CmdletBinding()]
param(
    [string]$ManifestUrl,
    [string]$PackageBaseUrl,
    [string]$SigningKeyPath,
    [string]$PreviousManifestPath,
    [string]$PreviousSignaturePath
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Requirements = Join-Path $PSScriptRoot "requirements-build.txt"
$VirtualEnv = Join-Path $ProjectRoot ".venv-nexa-installer"
$BuildRoot = Join-Path $ProjectRoot "build\NexaInstallerRelease"
$AppDist = Join-Path $BuildRoot "app-dist"
$AppWork = Join-Path $BuildRoot "app-work"
$InstallerWork = Join-Path $BuildRoot "installer-work"
$SpecRoot = Join-Path $BuildRoot "spec"
$GeneratedConfig = Join-Path $BuildRoot "release-config.json"
$InstallerOutput = Join-Path $ProjectRoot "dist"
$Python = Join-Path $VirtualEnv "Scripts\python.exe"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Zum Bauen wird Python auf diesem Build-PC benötigt. Die erzeugte NexaInstaller.exe enthält ihre eigene Laufzeit."
}

if (-not (Test-Path $Python)) {
    & python -m venv $VirtualEnv
    if ($LASTEXITCODE -ne 0) { throw "Die Build-Virtualenv konnte nicht erstellt werden." }
}

& $Python -m pip install --disable-pip-version-check -r $Requirements
if ($LASTEXITCODE -ne 0) { throw "Build-Abhängigkeiten konnten nicht installiert werden." }

$NexaVersion = & $Python (Join-Path $PSScriptRoot "release_tools.py") `
    project-version --main-file (Join-Path $ProjectRoot "main.py")
if ($LASTEXITCODE -ne 0) { throw "Die Nexa-Version konnte nicht aus main.py ermittelt werden." }
$NexaVersion = ($NexaVersion | Select-Object -Last 1).Trim()
if ($NexaVersion -notmatch '^\d+\.\d+\.\d+$') {
    throw "Ungültige Nexa-Versionsnummer in main.py: $NexaVersion"
}

$Config = Get-Content (Join-Path $PSScriptRoot "release-config.json") -Raw |
    ConvertFrom-Json
if ($ManifestUrl) {
    $Config.manifest_url = $ManifestUrl
}
if ($SigningKeyPath) {
    if (-not $PackageBaseUrl) {
        throw "-PackageBaseUrl muss beim Signieren ein HTTPS-Verzeichnis für das ZIP-Paket angeben."
    }
    if (-not (Test-Path $SigningKeyPath -PathType Leaf)) {
        throw "Ed25519-Privatschlüssel nicht gefunden: $SigningKeyPath"
    }
    $PublicKey = & $Python (Join-Path $PSScriptRoot "release_tools.py") `
        public-key --key (Resolve-Path $SigningKeyPath).Path
    if ($LASTEXITCODE -ne 0) { throw "Der Ed25519-Privatschlüssel ist ungültig." }
    $Config.ed25519_public_key = ($PublicKey | Select-Object -Last 1).Trim()
}
if ([bool]$PreviousManifestPath -ne [bool]$PreviousSignaturePath) {
    throw "-PreviousManifestPath und -PreviousSignaturePath müssen gemeinsam angegeben werden."
}
if ($PreviousManifestPath) {
    if (-not (Test-Path $PreviousManifestPath -PathType Leaf)) {
        throw "Vorheriges Manifest nicht gefunden: $PreviousManifestPath"
    }
    if (-not (Test-Path $PreviousSignaturePath -PathType Leaf)) {
        throw "Vorherige Manifest-Signatur nicht gefunden: $PreviousSignaturePath"
    }
}

if ($Config.manifest_url -notmatch '^(https://|http://)') {
    throw "Die Release-Manifest-URL muss HTTPS oder eine lokale/private HTTP-URL verwenden."
}
if ($Config.manifest_url -match '^http://') {
    $uri = [uri]$Config.manifest_url
    $hostname = $uri.Host
    if ($hostname -notin @('localhost','127.0.0.1','::1') -and -not ($hostname -match '^192\.168\.|^10\.|^172\.(1[6-9]|2[0-9]|3[0-1])\.|^127\.|^::1$')) {
        throw "Private/local HTTP-Manifest-URLs sind nur für localhost und private LAN-IPv4-Adressen erlaubt."
    }
}

New-Item -ItemType Directory -Force -Path $BuildRoot, $SpecRoot, $InstallerOutput |
    Out-Null
$Config | ConvertTo-Json | Set-Content -Encoding utf8 $GeneratedConfig
$env:NEXA_RELEASE_CONFIG_PATH = $GeneratedConfig

Push-Location $ProjectRoot
try {
    Write-Host "Baue Nexa $NexaVersion als portable Windows-x64-Anwendung ..."
    & $Python -m PyInstaller --noconfirm --clean --onedir `
        --name Nexa `
        --distpath $AppDist `
        --workpath $AppWork `
        --specpath $SpecRoot `
        --icon (Join-Path $ProjectRoot "NexaRuntime.ico") `
        --add-data "$(Join-Path $ProjectRoot 'NexaRuntime.ico');." `
        (Join-Path $ProjectRoot "main.py")
    if ($LASTEXITCODE -ne 0) { throw "Der Nexa-Anwendungsbuild ist fehlgeschlagen." }
    Copy-Item -Force `
        (Join-Path $ProjectRoot "NexaRuntime.ico") `
        (Join-Path $AppDist "Nexa\NexaRuntime.ico")

    & $Python -m unittest -v installer.test_installer_core
    if ($LASTEXITCODE -ne 0) { throw "Die Installer-Sicherheitstests sind fehlgeschlagen." }
    $NexaExecutable = Join-Path $AppDist "Nexa\Nexa.exe"
    $VersionOutput = & $NexaExecutable --version
    if ($LASTEXITCODE -ne 0 -or ($VersionOutput -join "`n") -notmatch [regex]::Escape($NexaVersion)) {
        throw "Nexa.exe --version smoke test failed."
    }
    $HelpOutput = & $NexaExecutable help
    if ($LASTEXITCODE -ne 0 -or ($HelpOutput -join "`n") -notmatch "Verfügbare Befehle") {
        throw "Nexa.exe help smoke test failed."
    }
    $RunOutput = & $NexaExecutable run (Join-Path $ProjectRoot "mathe.nexa")
    if ($LASTEXITCODE -ne 0) { throw "Nexa.exe run mathe.nexa smoke test failed." }
    Write-Host "Nexa --version, help und run mathe.nexa: OK"

    & $Python (Join-Path $PSScriptRoot "smoke_test_install.py") `
        --app-directory (Join-Path $AppDist "Nexa") `
        --sample-file (Join-Path $ProjectRoot "mathe.nexa") `
        --version $NexaVersion
    if ($LASTEXITCODE -ne 0) { throw "Installed nexa.cmd smoke test failed." }

    if ($SigningKeyPath) {
        if (-not $PackageBaseUrl) {
            throw "PackageBaseUrl fehlt."
        }
        Write-Host "Erzeuge und signiere das Nexa-Release ..."
        $ReleaseArguments = @(
            "package",
            "--app-directory", (Join-Path $AppDist "Nexa"),
            "--output-directory", (Join-Path $BuildRoot "release"),
            "--version", $NexaVersion,
            "--manifest-url", $Config.manifest_url,
            "--package-base-url", $PackageBaseUrl,
            "--signing-key", (Resolve-Path $SigningKeyPath).Path
        )
        if ($PreviousManifestPath) {
            $ReleaseArguments += @(
                "--previous-manifest", (Resolve-Path $PreviousManifestPath).Path,
                "--previous-signature", (Resolve-Path $PreviousSignaturePath).Path
            )
        }
        & $Python (Join-Path $PSScriptRoot "release_tools.py") @ReleaseArguments
        if ($LASTEXITCODE -ne 0) { throw "Das signierte Release konnte nicht erstellt werden." }
    }
    else {
        Write-Warning "Kein Signing-Key angegeben: Es wird kein verteilbares Release-Manifest erzeugt."
    }

    Write-Host "Baue den grafischen NexaInstaller ..."
    & $Python -m PyInstaller --noconfirm --clean `
        --distpath $InstallerOutput `
        --workpath $InstallerWork `
        (Join-Path $ProjectRoot "NexaInstaller.spec")
    if ($LASTEXITCODE -ne 0) { throw "Der NexaInstaller-Build ist fehlgeschlagen." }

    $Executable = Join-Path $InstallerOutput "NexaInstaller.exe"
    if (-not (Test-Path $Executable -PathType Leaf)) {
        throw "PyInstaller meldete Erfolg, aber die EXE fehlt: $Executable"
    }
    Write-Host ""
    Write-Host "NexaInstaller.exe erstellt: $Executable"
    Write-Host "Nexa-Version im Installer-Paket: $NexaVersion"
    if (-not $Config.ed25519_public_key) {
        Write-Warning "Vor einer Veröffentlichung release-config.json mit Server-URL und öffentlichem Ed25519-Schlüssel konfigurieren und neu bauen."
    }
}
finally {
    Remove-Item Env:\NEXA_RELEASE_CONFIG_PATH -ErrorAction SilentlyContinue
    Pop-Location
}
