# Download the three MiniMax-H3-Image weights this setup needs, straight from
# ModelScope, and verify each one against its exact byte count before accepting it.
#
#   powershell -ExecutionPolicy Bypass -File scripts\fetch_weights.ps1 -Target C:\ComfyUI\...\ComfyUI\models
#
# ModelScope 直链实测 9-11 MB/s；curl.exe 自带断点续传（-C -），断了重跑即可。
param(
  [string]$Target = ".\models",
  [switch]$SkipExisting
)

$ErrorActionPreference = 'Stop'

$Files = @(
  @{
    Name = 'MiniMax-H3-Image-Pruned-Q3_K_M.gguf'
    Dir  = 'unet'
    Size = [long]8911771264
    Url  = 'https://www.modelscope.cn/api/v1/models/Abiray/MiniMax-H3-Image-GGUF/repo?Revision=master&FilePath=MiniMax-H3-Image-Pruned-Q3_K_M.gguf'
  },
  @{
    Name = 'qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors'
    Dir  = 'text_encoders'
    Size = [long]15687142551
    Url  = 'https://www.modelscope.cn/api/v1/models/Comfy-Org/MiniMax-H3/repo?Revision=master&FilePath=text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors'
  },
  @{
    Name = 'minimax_h3_image_vae_fp16.safetensors'
    Dir  = 'vae'
    Size = [long]1168505312
    Url  = 'https://www.modelscope.cn/api/v1/models/Comfy-Org/MiniMax-H3-Image/repo?Revision=master&FilePath=vae/minimax_h3_image_vae_fp16.safetensors'
  }
)

function Get-Size([string]$p) {
  if (-not (Test-Path $p)) { return [long]0 }
  return ([System.IO.FileInfo]::new($p)).Length
}

foreach ($f in $Files) {
  $dir = Join-Path $Target $f.Dir
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
  $out = Join-Path $dir $f.Name

  $have = Get-Size $out
  if ($have -eq $f.Size) {
    Write-Host "[skip] $($f.Name) already complete ($have bytes)" -ForegroundColor DarkGray
    continue
  }
  if ($have -gt 0 -and $SkipExisting) {
    Write-Host "[skip] $($f.Name) present but incomplete ($have / $($f.Size)), -SkipExisting set" -ForegroundColor Yellow
    continue
  }

  Write-Host "[get ] $($f.Name)  $($f.Size) bytes" -ForegroundColor Cyan
  # -C - resumes a partial file; --retry-all-errors covers transient network drops.
  & curl.exe -L -C - --retry 10 --retry-delay 5 --retry-all-errors -o $out $f.Url
  if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] curl exited $LASTEXITCODE for $($f.Name)" -ForegroundColor Red
    exit 1
  }

  $have = Get-Size $out
  if ($have -ne $f.Size) {
    Write-Host "[FAIL] $($f.Name): got $have bytes, expected $($f.Size)" -ForegroundColor Red
    Write-Host "       rerun this script; curl will resume from where it stopped." -ForegroundColor Yellow
    exit 1
  }
  Write-Host "[ok  ] $($f.Name) verified ($have bytes)" -ForegroundColor Green
}

Write-Host ''
Write-Host 'All weights present and verified.' -ForegroundColor Green
Write-Host "Place the two workflow JSONs from workflows\ into <ComfyUI>\ComfyUI\user\default\workflows\"
