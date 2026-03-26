param(
  [string]$Message = "Update Aung Market"
)

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot
$ErrorActionPreference = "Stop"

$python = if (Test-Path ".\.venv\Scripts\python.exe") {
  ".\.venv\Scripts\python.exe"
} else {
  "python"
}

Write-Host "Running Python checks..."
@'
import py_compile
py_compile.compile("app.py", doraise=True)
py_compile.compile("database.py", doraise=True)
py_compile.compile("forms.py", doraise=True)
py_compile.compile("wsgi.py", doraise=True)
print("Python checks passed.")
'@ | & $python -

if (-not (git status --short)) {
  Write-Host "No changes to commit."
  exit 0
}

Write-Host "Committing and pushing to GitHub..."
git add .
git commit -m $Message
git push origin main

Write-Host "Done."
