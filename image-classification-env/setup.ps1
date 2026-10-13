# 画像分類の学習環境セットアップ（Windows PowerShell）
#   powershell -ExecutionPolicy Bypass -File setup.ps1
#   $env:TORCH_VARIANT="cpu";   powershell -ExecutionPolicy Bypass -File setup.ps1   # 強制的に CPU 版
#   $env:TORCH_VARIANT="cu128"; powershell -ExecutionPolicy Bypass -File setup.ps1   # cu126 / cu128 / cu130
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$PyVersion = if ($env:PY_VERSION) { $env:PY_VERSION } else { "3.12" }

# 1) uv
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "[1/4] uv をインストールします"
    powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}
Write-Host "[1/4] $(uv --version)"

# 2) 仮想環境
Write-Host "[2/4] .venv を作成（Python $PyVersion）"
uv venv --python $PyVersion --allow-existing .venv
if ($LASTEXITCODE -ne 0) { throw "venv の作成に失敗しました" }

# 3) PyTorch
$variant = if ($env:TORCH_VARIANT) { $env:TORCH_VARIANT } else { "auto" }
if ($variant -eq "auto") {
    $variant = "cpu"
    if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
        $m = (nvidia-smi | Out-String) | Select-String -Pattern "CUDA Version: (\d+)\.(\d+)"
        if ($m) {
            $v = [int]$m.Matches[0].Groups[1].Value * 100 + [int]$m.Matches[0].Groups[2].Value
            if     ($v -ge 1300) { $variant = "cu130" }
            elseif ($v -ge 1208) { $variant = "cu128" }
            elseif ($v -ge 1206) { $variant = "cu126" }
            else { Write-Warning "GPU ドライバが古いため CPU 版を入れます。ドライバ更新後に再実行してください。" }
        }
    }
}
Write-Host "[3/4] PyTorch をインストール（$variant）"
uv pip install --python .venv torch torchvision --index-url "https://download.pytorch.org/whl/$variant"
if ($LASTEXITCODE -ne 0) { throw "PyTorch のインストールに失敗しました" }

# 4) その他
Write-Host "[4/4] ライブラリをインストール"
uv pip install --python .venv -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "ライブラリのインストールに失敗しました" }

Write-Host ""
Write-Host "セットアップ完了。動作確認:"
Write-Host "  .\.venv\Scripts\Activate.ps1; python scripts\verify_env.py"
