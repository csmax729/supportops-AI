# Run from PowerShell on Windows. Ctrl+C shuts down the processes started here.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$pythonPath = (Resolve-Path ".venv/Scripts/python.exe").Path
$modelPath = "runtime/llama/model.gguf"
$serverPath = "runtime/llama/llama-server.exe"
if (!(Test-Path $modelPath) -or !(Test-Path $serverPath)) {
    throw "Place the llama.cpp CPU server and GGUF model in runtime/llama, or follow the Ollama quick start in README.md."
}
& $pythonPath -m scripts.bootstrap
$env:PROVIDER = "llamacpp"
$env:CHAT_MODEL = "qwen2.5-1.5b-instruct"
$env:LLAMA_URL = "http://127.0.0.1:8080"
$env:API_URL = "http://127.0.0.1:8000"
$env:PROVIDER_TIMEOUT = "240"
$env:OMP_NUM_THREADS = "4"
$env:HF_HOME = Join-Path (Get-Location).Path "runtime/hf"
foreach ($port in 8080,8000,8501) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is in use. Stop its service before starting the local stack."
    }
}
$children = @()
try {
    $children += Start-Process -FilePath $serverPath -ArgumentList "-m $modelPath --host 127.0.0.1 --port 8080 -c 8192 -t 4" -WindowStyle Hidden -PassThru -RedirectStandardOutput runtime/model.out -RedirectStandardError runtime/model.err
    $children += Start-Process -FilePath $pythonPath -ArgumentList "-m uvicorn backend.main:create_app --factory --host 127.0.0.1 --port 8000" -WindowStyle Hidden -PassThru -RedirectStandardOutput runtime/api.out -RedirectStandardError runtime/api.err
    Write-Host "Open http://127.0.0.1:8501 after Streamlit starts. Ctrl+C stops the stack."
    & $pythonPath -m streamlit run frontend/app.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true
} finally {
    foreach ($child in $children) {
        if (!$child.HasExited) { taskkill.exe /PID $child.Id /T /F | Out-Null }
    }
}
