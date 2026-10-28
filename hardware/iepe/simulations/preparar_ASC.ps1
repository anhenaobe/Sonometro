# Crea esquematicos .asc usando el simbolo LT3092 ya instalado en LTspice.
# Los pines del .asy se buscan por nombre para no suponer coordenadas.
$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$roots = @(
    (Join-Path $env:LOCALAPPDATA 'LTspice\lib\sym'),
    'C:\Program Files\ADI\LTspice\lib\sym',
    'C:\Program Files\LTC\LTspiceXVII\lib\sym'
)
$sym = $null
$root = $null
foreach ($r in $roots) {
 if (Test-Path $r) {
  $hit = Get-ChildItem -Path $r -Filter 'LT3092.asy' -Recurse -File -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($hit) { $sym=$hit; $root=$r; break }
 }
}
if (!$sym) { throw 'No se encontro LT3092.asy. Actualiza los modelos desde LTspice o usa el demo oficial de ADI.' }
Write-Host "Simbolo LT3092 localizado: $($sym.FullName)"
$relative = $sym.FullName.Substring($root.Length+1).Replace('.asy','')
$pinInfo=@{}
$lastPin=$null
foreach ($line in (Get-Content $sym.FullName)) {
 if ($line -match '^PIN\s+(-?\d+)\s+(-?\d+)') { $lastPin=@([int]$Matches[1],[int]$Matches[2]); continue }
 if ($line -match '^PINATTR\s+PinName\s+(\S+)' -and $lastPin) { $pinInfo[$Matches[1].ToUpper()]=$lastPin }
}
foreach ($name in @('IN','SET','OUT')) { if (!$pinInfo.ContainsKey($name)) { throw "Sin pin $name en LT3092.asy" } }
function Native([string]$name) {
 $ax=432; $ay=224
 return "SYMBOL $relative $ax $ay R0`r`nSYMATTR InstName U1`r`n"
}
function FlagPin([string]$name,[string]$net) {
 $pair=$pinInfo[$name]
 return "FLAG $([int]$pair[0]+432) $([int]$pair[1]+224) $net`r`n"
}
function AddRes([int]$x,[int]$y,[string]$id,[string]$value,[string]$na,[string]$nb) {
 return "SYMBOL res $x $y R0`r`nSYMATTR InstName $id`r`nSYMATTR Value $value`r`nFLAG $($x+16) $($y+16) $na`r`nFLAG $($x+16) $($y+96) $nb`r`n"
}
function AddVolt([int]$x,[int]$y,[string]$id,[string]$value,[string]$na,[string]$nb) {
 return "SYMBOL voltage $x $y R0`r`nSYMATTR InstName $id`r`nSYMATTR Value $value`r`nFLAG $x $($y+16) $na`r`nFLAG $x $($y+96) $nb`r`n"
}
function AddCap([int]$x,[int]$y,[string]$id,[string]$value,[string]$na,[string]$nb) {
 return "SYMBOL cap $x $y R0`r`nSYMATTR InstName $id`r`nSYMATTR Value $value`r`nFLAG $($x+16) $y $na`r`nFLAG $($x+16) $($y+64) $nb`r`n"
}
function Build([string]$file,[bool]$filtered,[bool]$dc) {
 $s="Version 4`r`nSHEET 1 1050 720`r`n"
 $s += (Native 'U1')
 $s += (FlagPin 'IN' 'VCC')
 $s += (FlagPin 'SET' 'SET')
 $s += (FlagPin 'OUT' 'REG')
 $s += (AddVolt 96 224 'V1' '24' 'VCC' '0')
 if ($filtered) { $rs='120k'; $ro='430' } else { $rs='20k'; $ro='71.5' }
 $s += (AddRes 624 224 'RSET' $rs 'SET' 'IEPE')
 $s += (AddRes 768 224 'ROUT' $ro 'REG' 'IEPE')
 if ($filtered) {
   $s += (AddCap 624 384 'CSET' '100n' 'SET' 'IEPE')
   $s += (AddRes 96 400 'RCOMP' '1k' 'VCC' 'COMP')
   $s += (AddCap 240 400 'CCOMP' '10n' 'COMP' 'IEPE')
 }
 if ($dc) {
   $s += (AddRes 896 224 'RLOAD' '{RL}' 'IEPE' '0')
   $cmd='.param RL=4.46k\n.step param RL list 1k 2.2k 4.46k 6.8k 8.2k 9k\n.op\n.meas OP I_IEPE PARAM I(RLOAD)\n.meas OP V_IEPE PARAM V(IEPE)'
 } else {
   $s += (AddRes 896 224 'RMIC' '50' 'IEPE' 'MIC')
   $s += (AddVolt 896 384 'VMIC' 'SINE(12.5 0.05 1k)' 'MIC' '0')
   $s += (AddCap 768 384 'CCABLE' '1n' 'IEPE' '0')
   if ($filtered) { $time='.tran 0 100m 70m 1u'; $fr='80m'; $to='100m' }
   else { $time='.tran 0 25m 10m 1u'; $fr='15m'; $to='25m' }
   $cmd="$time\n.meas TRAN IAVG AVG I(RMIC) FROM=$fr TO=$to\n.meas TRAN IMAX MAX I(RMIC) FROM=$fr TO=$to\n.meas TRAN IMIN MIN I(RMIC) FROM=$fr TO=$to\n.meas TRAN VMAX MAX V(IEPE) FROM=$fr TO=$to\n.meas TRAN VMIN MIN V(IEPE) FROM=$fr TO=$to"
 }
 $s+="TEXT 96 576 Left 2 !$cmd`r`n"
 $s+="TEXT 96 64 Left 2 ;FUENTE IEPE LT3092 - SIMBOLO Y MODELO NATIVOS (ADI)`r`n"
 $s+="TEXT 96 96 Left 2 ;Modelos de mic/cable simplificados, sin resultados medidos`r`n"
 $out=Join-Path $base $file
 Set-Content -Path $out -Value $s -Encoding Default
 Write-Host "Creado $file"
}
Build '01_LT3092_DC.asc' $false $true
Build '02_LT3092_MIC_1kHz.asc' $false $false
Build '03_LT3092_FILTRADO_1kHz.asc' $true $false
Write-Host 'Abre los archivos .asc en LTspice y ejecuta Run. Ctrl+L para los resultados.'
