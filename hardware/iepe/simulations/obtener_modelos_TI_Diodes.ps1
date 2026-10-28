$ErrorActionPreference = "Stop"
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "Descargando modelos desde los fabricantes (uso y licencias del fabricante)..."
$tiZip = Join-Path $base 'SBOM862F.zip'
$tiDir = Join-Path $base 'TI_extraido'
New-Item -ItemType Directory -Force -Path $tiDir | Out-Null
Invoke-WebRequest -Uri 'https://www.ti.com/lit/zip/sbom862' -OutFile $tiZip -UseBasicParsing
Expand-Archive -Path $tiZip -DestinationPath $tiDir -Force
$allFiles = Get-ChildItem $tiDir -Recurse -File | Where-Object { $_.Extension -match '^\.(lib|cir|txt|mod|sub)$' }
$match = $null
$modelName = $null
foreach ($file in $allFiles) {
    $line = Select-String -Path $file.FullName -Pattern '^\s*\.SUBCKT\s+(OPA192|OPAx192)\s+' -CaseSensitive:$false | Select-Object -First 1
    if ($line) { $match = $file; $modelName = ([regex]::Match($line.Line,'(?i)^\s*\.SUBCKT\s+(OPA192|OPAx192)\s+')).Groups[1].Value; Write-Host "Modelo OPA: $($file.Name) -- $($line.Line)"; break }
}
if ($null -eq $match) {
    Write-Warning 'No se detecto el subcircuito del OPA192. Inspecciona el ZIP y los ficheros descargados.'
} else {
    Copy-Item $match.FullName (Join-Path $base 'OPA192.lib') -Force
    Write-Host 'Preparado OPA192.lib'
    if ($modelName -ieq 'OPAx192') {
      foreach ($name in @('04_OPA192_BSS84_1kHz.cir','05_OPA192_BSS84_DC.cir','07_OPA192_BSS84_IMPEDANCIA_AC.cir')) {
        $fileName = Join-Path $base $name
        (Get-Content $fileName -Raw).Replace('DRIVE OPA192','DRIVE OPAx192') | Set-Content -Encoding Default $fileName
      }
      Write-Host 'Adaptadas llamadas a OPAx192 en los 3 circuitos.'
    }
}
Invoke-WebRequest -Uri 'https://www.diodes.com/spice/download/2330/BSS84.spice.txt' -OutFile (Join-Path $base 'BSS84.spice.txt') -UseBasicParsing
Write-Host 'Preparado BSS84.spice.txt'
Write-Host 'Comprueba que los modelos incluyen .SUBCKT OPA192 y .SUBCKT BSS84 antes de Run.'
