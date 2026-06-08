# Warm-start validation test: runs LNS -> emits feasible DSL -> solves with main.py
#
# For each problem type (using smallest instance), this script:
#   1. Runs example_lns.py with --emit-feasible-dsl to produce a warm-start DSL
#   2. Runs main.py on that DSL and checks for clean exit + solution/bound output
#
# Usage:  .\test_warm_starts.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".\.venv\Scripts\python.exe"
$ExampleLnS = Join-Path $RepoRoot "example_lns.py"
$MainPy = Join-Path $RepoRoot "main.py"
$TempDir = Join-Path $RepoRoot ".tmp_warm_start_tests"

# Ensure clean temp directory
if (Test-Path $TempDir) { Remove-Item -Recurse -Force $TempDir }
New-Item -ItemType Directory -Path $TempDir | Out-Null

$Passed = 0
$Failed = 0
$Skipped = 0

Push-Location $RepoRoot
try {
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Magenta
    Write-Host "  WARM-START VALIDATION TESTS  (LNS -> DSL -> main.py)" -ForegroundColor Magenta
    Write-Host ("=" * 70) -ForegroundColor Magenta

    # Problem definitions: Key, DSL path, description, initializer, iterations, extra LNS args
    $TestCases = @(
        @{
            Key     = "1dbp"
            File    = "problem_instances\1dbp\problem_2_t_zero_based.dsl"
            Desc    = "1D Bin Packing (2 items)"
            Init    = "greedy"
            Iters   = 500
            LnsArgs = @()
        },
        @{
            Key     = "2dbp"
            File    = "problem_instances\2dbp\random_2dbp_zero_based.dsl"
            Desc    = "2D Bin Packing (small)"
            Init    = "greedy"
            Iters   = 500
            LnsArgs = @("--init-scoring", "feasibility-first", "--init-restarts", "32")
        },
        @{
            Key     = "cvrp"
            File    = "problem_instances\cvrp\random_euclidean_cvrp_8.dsl"
            Desc    = "CVRP (8 customers)"
            Init    = "cvrp"
            Iters   = 500
            LnsArgs = @()
        }
        # JSSP omitted: MiniZinc warm_start does not yet support nested (2D) array hints.
    )

    foreach ($tc in $TestCases) {
        $Key   = $tc.Key
        $File  = $tc.File
        $Desc  = $tc.Desc
        $Init  = $tc.Init
        $Iters = $tc.Iters
        $ExtraArgs = $tc.LnsArgs

        Write-Host ""
        Write-Host ("-" * 70) -ForegroundColor Cyan
        Write-Host "  WARM-START TEST: [$Key] $Desc" -ForegroundColor Cyan
        Write-Host ("-" * 70) -ForegroundColor Cyan

        if (-not (Test-Path $File)) {
            Write-Host "  [SKIP]  DSL file not found: $File" -ForegroundColor Yellow
            $Skipped++
            continue
        }

        $tempDsl = Join-Path $TempDir "${Key}_warm_start.dsl"

        # Step 1: Build and run LNS command
        $lnsArgs = @(
            $ExampleLnS,
            $File,
            "--initializer", $Init,
            "--max-iterations", $Iters,
            "--emit-feasible-dsl", $tempDsl,
            "--emit-feasible-on", "incumbent"
        )
        if ($ExtraArgs.Count -gt 0) {
            $lnsArgs += $ExtraArgs
        }

        Write-Host "  [1/3] Running LNS (emit warm-start to $tempDsl) ..." -ForegroundColor DarkGray
        $start = Get-Date
        try {
            $lnsProcess = Start-Process -FilePath $Python `
                -ArgumentList $lnsArgs `
                -NoNewWindow -Wait -PassThru `
                -RedirectStandardOutput (Join-Path $TempDir "${Key}_lns_stdout.txt") `
                -RedirectStandardError  (Join-Path $TempDir "${Key}_lns_stderr.txt")

            $elapsed = "{0:N2}s" -f ((Get-Date) - $start).TotalSeconds

            if ($lnsProcess.ExitCode -ne 0) {
                Write-Host "  [1/3] LNS exited with code $($lnsProcess.ExitCode) after $elapsed" -ForegroundColor Red
                $stderr = Get-Content (Join-Path $TempDir "${Key}_lns_stderr.txt") -Raw
                Write-Host "         stderr: $($stderr.TrimEnd() -replace '\r\n', ' | ')" -ForegroundColor Red
                $Failed++
                continue
            }

            Write-Host "  [1/3] LNS completed in $elapsed" -ForegroundColor Gray

            # Check if warm-start file was actually written
            if (-not (Test-Path $tempDsl)) {
                Write-Host "  [2/3] LNS did not produce warm-start DSL (no incumbent found?)" -ForegroundColor Red
                $Failed++
                continue
            }

            Write-Host "  [2/3] Warm-start DSL created ($($tempDsl))" -ForegroundColor Gray

        } catch {
            Write-Host "  [1/3] LNS threw exception: $_" -ForegroundColor Red
            $Failed++
            continue
        }

        # Step 2: Run main.py on the warm-start DSL
        Write-Host "  [3/3] Running main.py (MiniZinc) on warm-start DSL (15s timeout) ..." -ForegroundColor DarkGray
        $start = Get-Date
        try {
            $solveProcess = Start-Process -FilePath $Python `
                -ArgumentList ($MainPy, $tempDsl, "--timelimit", "15") `
                -NoNewWindow -Wait -PassThru `
                -RedirectStandardOutput (Join-Path $TempDir "${Key}_solve_stdout.txt") `
                -RedirectStandardError  (Join-Path $TempDir "${Key}_solve_stderr.txt")

            $elapsed = "{0:N2}s" -f ((Get-Date) - $start).TotalSeconds
            $exitCode = $solveProcess.ExitCode

            $stdout = Get-Content (Join-Path $TempDir "${Key}_solve_stdout.txt") -Raw
            $stderr = Get-Content (Join-Path $TempDir "${Key}_solve_stderr.txt") -Raw

            if ($exitCode -ne 0) {
                Write-Host "  [3/3] main.py exited with code $exitCode after $elapsed" -ForegroundColor Red
                if ($stderr) {
                    Write-Host "         stderr: $($stderr.TrimEnd() -replace '\r\n', ' | ')" -ForegroundColor Red
                }
                $Failed++
                continue
            }

            # Check for solution/bound output (case-insensitive)
            $fullOutput = "$stdout`n$stderr"
            $hasSolution = $fullOutput -match "(?i)(optimization result|bound|optimal|solution|makespan|lower.?bound|upper.?bound|infeasible)"

            if ($hasSolution) {
                Write-Host "  [3/3] main.py solved warm-start DSL in $elapsed" -ForegroundColor Green
                # Show relevant output lines
                $lines = $stdout -split "`n" | Where-Object { $_.Trim() -ne "" }
                $relevant = $lines | Select-Object -Last 5
                foreach ($l in $relevant) { Write-Host "    $l" }
                $Passed++
            } else {
                Write-Host "  [3/3] main.py exited OK but no solution/bound output detected!" -ForegroundColor Red
                Write-Host "         stdout preview:" -ForegroundColor Red
                $first10 = ($stdout -split "`n") | Where-Object { $_.Trim() -ne "" } | Select-Object -First 10
                foreach ($l in $first10) { Write-Host "    $l" }
                $Failed++
            }
        } catch {
            Write-Host "  [3/3] main.py threw exception: $_" -ForegroundColor Red
            $Failed++
        }
    }

    # Summary
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Magenta
    Write-Host "  WARM-START TEST SUMMARY" -ForegroundColor Magenta
    Write-Host ("=" * 70) -ForegroundColor Magenta
    Write-Host "  PASSED:  $Passed" -ForegroundColor Green
    if ($Skipped -gt 0) { Write-Host "  SKIPPED: $Skipped" -ForegroundColor Yellow }
    if ($Failed -gt 0) { Write-Host "  FAILED:  $Failed" -ForegroundColor Red }
    Write-Host ""

} finally {
    Pop-Location

    # Cleanup temp directory
    if (Test-Path $TempDir) {
        Write-Host "  Cleaning up $TempDir ..." -ForegroundColor DarkGray
        Remove-Item -Recurse -Force $TempDir
    }
}

# Exit with non-zero if any test failed
if ($Failed -gt 0) {
    Exit 1
}
