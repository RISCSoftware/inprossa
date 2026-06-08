# Smoke-test script: runs main.py (MiniZinc) and example_lns.py (LNS)
# on the smallest instance of each problem type.
#
# Usage:  .\test_all.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = "$RepoRoot\.venv\Scripts\python.exe"

function Invoke-Test {
    param (
        [string]$Name,
        [string]$Command,
        [string]$Description
    )

    $out = "$Name :: $Description"
    Write-Host ""
    Write-Host ("-" * 70) -ForegroundColor Cyan
    Write-Host "  TEST: $out" -ForegroundColor Cyan
    Write-Host ("-" * 70) -ForegroundColor Cyan

    $start = Get-Date
    try {
        $result = Invoke-Expression "$Python $Command 2>&1"
        $elapsed = "{0:N2}s" -f ((Get-Date) - $start).TotalSeconds
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [PASS]  ($elapsed)" -ForegroundColor Green
            # Show last 5 lines for quick sanity check
            $lines = $result -split "`n" | Where-Object { $_.Trim() -ne "" }
            $last = $lines | Select-Object -Last 5
            foreach ($l in $last) { Write-Host "    $l" }
        } else {
            Write-Host "  [FAIL]  (exit $LASTEXITCODE)  after $elapsed" -ForegroundColor Red
            foreach ($l in $result) { Write-Host "    $l" }
        }
    } catch {
        Write-Host "  [ERROR]  $_" -ForegroundColor Red
    }
}

# smallest instance per problem type
$Problems = @{
    "1dbp"  = @{
        File   = "problem_instances\1dbp\problem_2_t_zero_based.dsl"
        Init   = "greedy"
        Iters  = 500
        Desc   = "1D Bin Packing (2 items)"
        LnsArgs = ""
    }
    "2dbp"  = @{
        File   = "problem_instances\2dbp\random_2dbp_zero_based.dsl"
        Init   = "greedy"
        Iters  = 500
        Desc   = "2D Bin Packing (small)"
        LnsArgs = "--init-scoring feasibility-first --init-restarts 32 --log-every 10"
    }
    "cvrp"  = @{
        File   = "problem_instances\cvrp\random_euclidean_cvrp_8.dsl"
        Init   = "cvrp"
        Iters  = 500
        Desc   = "CVRP (8 customers)"
        LnsArgs = ""
    }
    "jssp"  = @{
        File   = "problem_instances\jssp\jssp_2x2.dsl"
        Init   = "jssp"
        Iters  = 500
        Desc   = "Job Shop 2x2"
        LnsArgs = ""
    }
}

Push-Location $RepoRoot
try {

    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Magenta
    Write-Host "  OPTDSL SMOKE TEST  (main.py + example_lns.py on each problem)" -ForegroundColor Magenta
    Write-Host ("=" * 70) -ForegroundColor Magenta

    foreach ($key in @("1dbp", "2dbp", "cvrp", "jssp")) {
        $p = $Problems[$key]
        $dslPath = $p.File
        $desc    = $p.Desc
        $init    = $p.Init
        $iters   = $p.Iters
        $lnsArgs = $p.LnsArgs

        if (-not (Test-Path $dslPath)) {
            Write-Host "  [SKIP]  [$key] file not found: $dslPath" -ForegroundColor Yellow
            continue
        }

        # main.py (MiniZinc solver)
        Invoke-Test -Name $key `
            -Command "main.py `"$dslPath`" --timelimit 30" `
            -Description "main.py (MiniZinc) -- $desc"

        # example_lns.py (LNS baseline)
        $lnsCmd = "example_lns.py `"$dslPath`" " `
            + "--initializer $init " `
            + "--max-iterations $iters " `
            + "--lns-destroy-fraction 0.25 " `
            + "--repair-samples 4 " `
            + "--random-seed 42"
        if ($lnsArgs -and $lnsArgs.Trim() -ne "") {
            $lnsCmd += " " + $lnsArgs
        }

        Invoke-Test -Name $key `
            -Command $lnsCmd `
            -Description "example_lns.py (LNS $init, $iters iters) -- $desc"
    }

    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Magenta
    Write-Host "  ALL TESTS COMPLETE" -ForegroundColor Magenta
    Write-Host ("=" * 70) -ForegroundColor Magenta

} finally {
    Pop-Location
}