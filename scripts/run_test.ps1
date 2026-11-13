# Submit an API-format prompt to a running ComfyUI and wait for the image.
#
#   powershell -ExecutionPolicy Bypass -File scripts\run_test.ps1 `
#              -PromptFile workflows\api_prompt_img2img.json -TimeoutMin 40
param(
  [string]$Api = 'http://127.0.0.1:8188',
  [Parameter(Mandatory = $true)][string]$PromptFile,
  [int]$TimeoutMin = 40
)
$ErrorActionPreference = 'Stop'

$prompt = Get-Content $PromptFile -Raw | ConvertFrom-Json
$body = @{ prompt = $prompt; client_id = 'h3image-test' } | ConvertTo-Json -Depth 30 -Compress

Write-Output "[$(Get-Date -f HH:mm:ss)] submitting $PromptFile ..."
try {
  $resp = Invoke-RestMethod -Uri "$Api/prompt" -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 60
} catch {
  Write-Output "SUBMIT FAILED: $($_.Exception.Message)"
  if ($_.ErrorDetails) {
    $e = $_.ErrorDetails.Message | ConvertFrom-Json
    $e.error | ForEach-Object { Write-Output "  $($_.type): $($_.message)" }
    $e.node_errors | ConvertTo-Json -Depth 8 | Write-Output
  }
  exit 1
}
if ($resp.error) {
  Write-Output "PROMPT ERROR:"
  $resp.error | ConvertTo-Json -Depth 6 | Write-Output
  exit 1
}
$promptId = $resp.prompt_id
Write-Output "[$(Get-Date -f HH:mm:ss)] prompt_id = $promptId"

$deadline = (Get-Date).AddMinutes($TimeoutMin)
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 20
  try {
    $hist = Invoke-RestMethod -Uri "$Api/history/$promptId" -TimeoutSec 30
  } catch { continue }
  if ($hist.PSObject.Properties.Name -contains $promptId) {
    $entry = $hist.$promptId
    Write-Output "[$(Get-Date -f HH:mm:ss)] status = $($entry.status.status_str)"
    if ($entry.status.messages) {
      $entry.status.messages | Where-Object { $_[0] -eq 'execution_error' } | ForEach-Object {
        Write-Output "EXECUTION ERROR:"
        $_[1] | ConvertTo-Json -Depth 6 | Write-Output
      }
    }
    if ($entry.outputs) {
      foreach ($k in $entry.outputs.PSObject.Properties.Name) {
        $o = $entry.outputs.$k
        if ($o.images) {
          foreach ($img in $o.images) {
            Write-Output "IMAGE: $($img.filename)  $($img.subfolder)  $($img.type)"
          }
        }
      }
      Write-Output "DONE"
      exit 0
    }
  } else {
    $q = Invoke-RestMethod -Uri "$Api/queue" -TimeoutSec 20
    Write-Output "[$(Get-Date -f HH:mm:ss)] running=$($q.queue_running.Count) pending=$($q.queue_pending.Count)"
  }
}
Write-Output "TIMEOUT after $TimeoutMin min"
exit 2
