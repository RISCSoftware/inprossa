# run_and_viz.ps1
# Usage:
#   .\run_and_viz.ps1 <dsl_file> [-Solver minizinc|lns|both] [-Initializer NAME]
#                     [-Iters N] [-LnsIters N] [-NoBrowser]
#
# -Initializer selects the LNS initializer, which also selects the operator pool
# (e.g. "2dbp" enables DBPClearBoxesDestroy/DBPClearItemsDestroy and
# DBPGreedyPlacementRepair/DBPFullRepackRepair). When omitted, a default is
# derived from the detected problem type.
#
# Examples:
#   .\run_and_viz.ps1 problem_instances\jssp\jssp_2x2.dsl
#   .\run_and_viz.ps1 problem_instances\cvrp\random_euclidean_cvrp_8.dsl -Solver both -LnsIters 100
#   .\run_and_viz.ps1 problem_instances\2dbp\random_2dbp_zero_based.dsl -Solver lns -Initializer 2dbp

param(
    [Parameter(Mandatory=$true, Position=0)][string]$DslFile,
    [Parameter(Mandatory=$false)][ValidateSet("minizinc","lns","both")][string]$Solver = "minizinc",
    [Parameter(Mandatory=$false)]
    [ValidateSet("greedy","random","mcmc","cvrp","jssp","2dbp","cutting_packing","woodcutting_pipeline")]
    [string]$Initializer = "",
    [Parameter(Mandatory=$false)][int]$Iters = 50,
    [Parameter(Mandatory=$false)][int]$LnsIters = 50,
    [Parameter(Mandatory=$false)][switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$Python = ".\.venv\Scripts\python.exe"
$RepoRoot = $PSScriptRoot
$TmpDir = Join-Path $RepoRoot "output\visualization"
$script:lnsSnapshotFile = $null

New-Item -ItemType Directory -Path $TmpDir -Force | Out-Null

function Get-ProblemType {
    param([string]$File)
    $path = $File.ToLower()
    if ($path -match "jssp") { return "jssp" }
    if ($path -match "2dbp")  { return "2dbp" }
    if ($path -match "cvrp")  { return "cvrp" }
    if ($path -match "1dbp")  { return "1dbp" }
    $content = Get-Content $File -Raw
    if ($content -match "jssp|JSSP|completion.*makespan") { return "jssp" }
    if ($content -match "2dbp|2D_BINPACK|two.?dimensional") { return "2dbp" }
    if ($content -match "cvrp|CVRP|vehicle_routing|arc_ij|city_tour") { return "cvrp" }
    return "1dbp"
}

function Get-Initializer {
    param([string]$Type)
    if ($Initializer) { return $Initializer }
    if ($Type -eq "cvrp") { return "cvrp" }
    if ($Type -eq "jssp") { return "jssp" }
    if ($Type -eq "2dbp") { return "2dbp" }
    return "greedy"
}

function Invoke-Solver {
    param([string]$Mode, [string]$Type)

    $init = Get-Initializer -Type $Type
    $resultFile = Join-Path $TmpDir ("result_$Mode.txt")

    if ($Mode -eq "minizinc") {
        $cmd = "& $Python run_minizinc.py `"$DslFile`" --timelimit 30 2>&1"
        $start = Get-Date
        $output = Invoke-Expression $cmd | Out-String
        $elapsed = "{0:N2}s" -f ((Get-Date) - $start).TotalSeconds
        $exitCode = $LASTEXITCODE
        $output | Out-File -FilePath $resultFile -Encoding UTF8
        Write-Host $output
        if ($exitCode -eq 0) {
            Write-Host "[OK] run_minizinc finished in $elapsed" -ForegroundColor Green
        } else {
            Write-Host "[FAIL] run_minizinc failed (exit $exitCode) after $elapsed" -ForegroundColor Red
        }
        return @{ ExitCode = $exitCode; ResultFile = $resultFile; Elapsed = $elapsed }
    } else {
        # LNS: use --emit-feasible-dsl to write a snapshot with @warm_start
        $snapshotFile = Join-Path $TmpDir ("lns_snapshot_$($Type)_$Mode.dsl")
        $script:lnsSnapshotFile = $snapshotFile
        $cmd = ("& $Python run_lns.py `"$DslFile`" " `
            + "--initializer $init " `
            + "--max-iterations $LnsIters " `
            + "--lns-destroy-fraction 0.25 " `
            + "--repair-samples 4 " `
            + "--random-seed 42 " `
            + "--print-assignment " `
            + "--emit-feasible-dsl `"$snapshotFile`" " `
            + "--emit-feasible-on incumbent " `
            + "--emit-feasible-every 1 2>&1")

        Write-Host ""
        Write-Host ("=" * 60) -ForegroundColor Cyan
        Write-Host "  [lns] $DslFile" -ForegroundColor Cyan
        Write-Host ("=" * 60) -ForegroundColor Cyan

        $start = Get-Date
        $output = Invoke-Expression $cmd | Out-String
        $elapsed = "{0:N2}s" -f ((Get-Date) - $start).TotalSeconds
        $exitCode = $LASTEXITCODE

        $output | Out-File -FilePath $resultFile -Encoding UTF8
        Write-Host $output

        if ($exitCode -eq 0) {
            Write-Host "[OK] lns finished in $elapsed" -ForegroundColor Green
        } else {
            Write-Host "[FAIL] lns failed (exit $exitCode) after $elapsed" -ForegroundColor Red
        }

        return @{ ExitCode = $exitCode; ResultFile = $resultFile; Elapsed = $elapsed; SnapshotFile = $snapshotFile }
    }
}

function Invoke-Visualizer {
    param([string]$Mode, [string]$Type)

    $resultFile = Join-Path $TmpDir ("result_$Mode.txt")
    $htmlFile   = Join-Path $TmpDir ("solution_${Mode}_${Type}.html")
    $title      = "OptDSL $Type :: $Mode :: $([System.IO.Path]::GetFileName($DslFile))"

    Write-Host ""
    Write-Host ("-" * 60) -ForegroundColor Yellow
    Write-Host "  Visualizing with $Type visualizer ..." -ForegroundColor Yellow
    Write-Host ("-" * 60) -ForegroundColor Yellow

    if ($Type -eq "jssp") {
        # For LNS mode, use the snapshot DSL (has @warm_start with completion matrix).
        # For main mode, use result text / result file.
        if ($Mode -eq "lns" -and $null -ne $script:lnsSnapshotFile -and (Test-Path $script:lnsSnapshotFile)) {
            $vizCmd = "& $Python Tools\visualize_jssp_solution.py --dsl-file `"$script:lnsSnapshotFile`" --output `"$htmlFile`" --title `"$title`" 2>&1"
        } else {
            $vizCmd = "& $Python Tools\visualize_jssp_solution.py --result-text (Get-Content $resultFile -Raw) --instance-file `"$DslFile`" --output `"$htmlFile`" --title `"$title`" 2>&1"
        }
    } elseif ($Type -eq "2dbp") {
        $vizCmd = "& $Python Tools\visualize_2dbp_solution.py --result-file `"$resultFile`" --dsl-file `"$DslFile`" --output `"$htmlFile`" --title `"$title`" 2>&1"
    } elseif ($Type -eq "cvrp") {
        # For LNS mode, use the snapshot DSL (has @warm_start with arcs/city_tour).
        # For main mode, use result file + original DSL.
        if ($Mode -eq "lns" -and $null -ne $script:lnsSnapshotFile -and (Test-Path $script:lnsSnapshotFile)) {
            $vizCmd = "& $Python Tools\visualize_cvrp_solution.py --dsl-file `"$script:lnsSnapshotFile`" --output `"$htmlFile`" --title `"$title`" 2>&1"
        } else {
            $vizCmd = "& $Python Tools\visualize_cvrp_solution.py --result-file `"$resultFile`" --dsl-file `"$DslFile`" --output `"$htmlFile`" --title `"$title`" 2>&1"
        }
    } else {
        Write-Host "  [SKIP] No visualizer for 1DBP" -ForegroundColor Yellow
        return $null
    }

    $output = Invoke-Expression $vizCmd | Out-String
    $exitCode = $LASTEXITCODE
    Write-Host $output

    if ($exitCode -eq 0 -and (Test-Path $htmlFile)) {
        Write-Host "[OK] HTML: $htmlFile" -ForegroundColor Green
        return $htmlFile
    } else {
        Write-Host "[FAIL] Visualizer failed (exit $exitCode)" -ForegroundColor Red
        return $null
    }
}

if (-not (Test-Path $DslFile)) {
    Write-Host "[ERROR] File not found: $DslFile" -ForegroundColor Red
    exit 1
}

$dslAbs = Resolve-Path $DslFile
$problemType = Get-ProblemType -File $dslAbs

Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Magenta
Write-Host "  OptDSL run_and_viz  |  file: $([System.IO.Path]::GetFileName($dslAbs))" -ForegroundColor Magenta
Write-Host "  Problem type detected: $problemType" -ForegroundColor Magenta
Write-Host ("=" * 70) -ForegroundColor Magenta

$htmlFiles = @()

if ($Solver -eq "minizinc" -or $Solver -eq "both") {
    $r = Invoke-Solver -Mode "minizinc" -Type $problemType
    if ($r.ExitCode -eq 0) {
        $h = Invoke-Visualizer -Mode "minizinc" -Type $problemType
        if ($h) { $htmlFiles += $h }
    }
}

if ($Solver -eq "lns" -or $Solver -eq "both") {
    $r = Invoke-Solver -Mode "lns" -Type $problemType
    if ($r.ExitCode -eq 0) {
        $h = Invoke-Visualizer -Mode "lns" -Type $problemType
        if ($h) { $htmlFiles += $h }
    }
}

if ($htmlFiles.Count -gt 0) {
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Magenta
    Write-Host "  $($htmlFiles.Count) visualization(s) written to $TmpDir" -ForegroundColor Magenta
    Write-Host ("=" * 70) -ForegroundColor Magenta

    if (-not $NoBrowser) {
        Write-Host ""
        Write-Host "  Opening in browser ..." -ForegroundColor Cyan
        foreach ($f in $htmlFiles) {
            Write-Host "  $f" -ForegroundColor Yellow
            Start-Process $f
        }
    }
} else {
    Write-Host ""
    Write-Host "[WARN] No visualizations produced. Check solver output above." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Output directory: $TmpDir" -ForegroundColor Gray