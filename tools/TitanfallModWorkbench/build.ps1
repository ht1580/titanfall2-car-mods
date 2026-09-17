[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Project

python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name TitanfallModWorkbench `
    --runtime-tmpdir "D:\CodexStorage\Temp" `
    --version-file version_info.txt `
    --add-data "vendor\blender;vendor\blender" `
    --add-data "vendor\legion;vendor\legion" `
    --add-data "vendor\tools;vendor\tools" `
    --add-data "vendor\rsx\rsx.exe;vendor\rsx" `
    --add-data "project-template.json;." `
    --add-data "animated-fx-recipe-template.json;." `
    --add-data "THIRD_PARTY_NOTICES.txt;." `
    app.py

if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }

$Exe = Join-Path $Project 'dist\TitanfallModWorkbench.exe'
if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) { throw "Missing output: $Exe" }
Get-FileHash -LiteralPath $Exe -Algorithm SHA256
Get-Item -LiteralPath $Exe | Select-Object FullName, Length, LastWriteTime
