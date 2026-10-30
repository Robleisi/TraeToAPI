# 用 Robleisi 自签名证书给 PE 文件签名（exe/dll）。
# 用法: powershell -NoProfile -ExecutionPolicy Bypass -File sign_exe.ps1 -Target <路径>
# 证书优先取当前用户存储里已有的 Robleisi 证书，否则从 certs/*.pfx 导入。

param(
    [Parameter(Mandatory = $true)][string]$Target,
    [string]$PfxPath = '',
    [string]$PfxPassword = 'TraeToAPI'
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $Target)) { throw "目标文件不存在: $Target" }
if (-not $PfxPath) { $PfxPath = Join-Path $PSScriptRoot '..\certs\robleisi-codesign.pfx' }

$cert = Get-ChildItem 'Cert:\CurrentUser\My' |
    Where-Object { $_.Subject -like 'CN=Robleisi*' -and $_.HasPrivateKey } |
    Select-Object -First 1

if (-not $cert) {
    if (-not (Test-Path $PfxPath)) {
        Write-Warning "无 Robleisi 签名证书，跳过签名（生成证书: scripts\make_signing_cert.ps1）"
        exit 0
    }
    $pw = ConvertTo-SecureString -String $PfxPassword -Force -AsPlainText
    Import-PfxCertificate -FilePath $PfxPath -CertStoreLocation 'Cert:\CurrentUser\My' -Password $pw | Out-Null
    $cert = Get-ChildItem 'Cert:\CurrentUser\My' |
        Where-Object { $_.Subject -like 'CN=Robleisi*' } | Select-Object -First 1
}

$sig = Set-AuthenticodeSignature -FilePath $Target -Certificate $cert -HashAlgorithm SHA256
if ($sig.Status -eq 'Valid') {
    Write-Host "已签名: $Target"
} else {
    Write-Warning "签名已写入但验证状态为 $($sig.Status): $($sig.StatusMessage)"
    Write-Warning "通常需要把根证书装进受信任的根存储: certutil -user -addstore Root certs\robleisi-codesign.cer"
}
