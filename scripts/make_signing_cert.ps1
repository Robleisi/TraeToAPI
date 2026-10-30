# 生成 Robleisi 自签名代码签名证书（本地开发/分发用）。
# 产出：
#   certs/robleisi-codesign.pfx  含私钥，签名用（密码见变量）
#   certs/robleisi-codesign.cer  公钥，装进受信任存储用
# 注意：
#   - 受信任的发布者存储可直接导入（不弹框）；
#   - 根存储（Root）导入时 Windows 会弹一次安全确认框，需手动点"是"：
#       certutil -user -addstore Root certs\robleisi-codesign.cer
#   - 私钥文件不要提交进仓库（certs/ 已在 .gitignore）。

$ErrorActionPreference = 'Stop'

$password = ConvertTo-SecureString -String 'TraeToAPI' -Force -AsPlainText
$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject 'CN=Robleisi, O=Robleisi' `
    -KeyUsage DigitalSignature `
    -KeyAlgorithm RSA -KeyLength 2048 `
    -FriendlyName 'Robleisi Code Signing' `
    -CertStoreLocation 'Cert:\CurrentUser\My' `
    -NotAfter (Get-Date).AddYears(10)

$certs = Join-Path $PSScriptRoot '..\certs'
New-Item -ItemType Directory -Force -Path $certs | Out-Null
Export-PfxCertificate -Cert $cert -FilePath (Join-Path $certs 'robleisi-codesign.pfx') -Password $password | Out-Null
Export-Certificate -Cert $cert -FilePath (Join-Path $certs 'robleisi-codesign.cer') | Out-Null

# 受信任的发布者：让系统认得"发布者 Robleisi"（不弹框）
Import-Certificate -FilePath (Join-Path $certs 'robleisi-codesign.cer') `
    -CertStoreLocation 'Cert:\CurrentUser\TrustedPublisher' | Out-Null

Write-Host "证书已生成: $($cert.Subject)"
Write-Host "Thumbprint: $($cert.Thumbprint)"
Write-Host "如签名验证仍显示 UntrustedRoot，执行:"
Write-Host "  certutil -user -addstore Root certs\robleisi-codesign.cer"
Write-Host "并在弹出的确认框点\"是\"。"
