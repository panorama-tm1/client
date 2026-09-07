# Local Windows build - the same command CI runs, for when you want an exe
# without going through a deploy.
#
#   .\build.ps1                          -> dev key, dist\panorama-client-dev.exe
#   .\build.ps1 demo C:\path\public_key.pem
param(
    [string]$Instance = "dev",
    [string]$KeyPath  = ""
)
$ErrorActionPreference = "Stop"

if ($KeyPath) { Copy-Item $KeyPath panorama_key.pem -Force }
$Instance | Set-Content -Path panorama_instance.txt -Encoding ascii

python -c "from cryptography.hazmat.primitives.serialization import load_pem_public_key; k=load_pem_public_key(open('panorama_key.pem','rb').read()); print('key: RSA', k.key_size)"

$safe = $Instance -replace '[^A-Za-z0-9._-]', '-'
nicegui-pack --onefile --windowed --clean `
    --name "panorama-client-$safe" `
    --add-data "panorama_key.pem;." `
    --add-data "panorama_instance.txt;." `
    main.py

Write-Host "-> dist\panorama-client-$safe.exe"
