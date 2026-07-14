<#
Demarre une instance uvicorn par entree de instances.json, chacune sur son
propre port, avec ses propres donnees et ses propres comptes
(DOSSIER_INSTANCE_DIR). Un process Python par instance, tous sur la meme
machine.

Creez d'abord une instance avec :
    python new_instance.py <nom> --port <port>

Puis lancez tout avec :
    .\launch_all.ps1

Chaque instance ecrit ses logs dans instances\<nom>\server.out.log et
server.err.log. Pour arreter : fermez les processus python (Get-Process
python) ou redemarrez la machine/le service qui les heberge.

Note d'encodage : ce fichier reste volontairement en ASCII (pas d'accents)
pour eviter le mojibake que PowerShell 5.1 introduit en lisant un script
UTF-8 sans BOM avec le codepage systeme par defaut.
#>

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$manifestPath = Join-Path $root "instances.json"

if (-not (Test-Path $manifestPath)) {
    Write-Error "instances.json introuvable -- creez d'abord une instance avec new_instance.py"
    exit 1
}

$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json

$names = $manifest.PSObject.Properties.Name
if ($names.Count -eq 0) {
    Write-Host "Aucune instance enregistree dans instances.json."
    exit 0
}

foreach ($name in $names) {
    $entry = $manifest.$name
    $relDir = $entry.dir -replace '/', '\'  # instances.json est toujours au format POSIX
    $instanceDir = Join-Path $root $relDir
    $outLog = Join-Path $instanceDir "server.out.log"
    $errLog = Join-Path $instanceDir "server.err.log"

    Write-Host "Demarrage de '$name' sur le port $($entry.port) (donnees : $($entry.dir))..."

    $env:DOSSIER_INSTANCE_DIR = $instanceDir
    Start-Process -FilePath "python" `
        -ArgumentList @("-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "$($entry.port)") `
        -WorkingDirectory $root `
        -RedirectStandardOutput $outLog `
        -RedirectStandardError $errLog `
        -WindowStyle Hidden
}
Remove-Item Env:\DOSSIER_INSTANCE_DIR -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Toutes les instances sont lancees."
Write-Host "Logs dans instances\<nom>\server.out.log / server.err.log"
Write-Host "Pour verifier : Get-Process python | Select-Object Id, StartTime"
