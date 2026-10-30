#!/usr/bin/env pwsh
# Builds wp1/InProSSA_Data_Management_Plan.pdf from the Markdown source.
# Requires: pandoc (>= 3.x) and a LaTeX engine (xelatex) on PATH.
#
# Usage:  pwsh wp1/build-pdf.ps1

$ErrorActionPreference = 'Stop'

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$out = Join-Path $here 'InProSSA_Data_Management_Plan.pdf'
$source = Join-Path $here 'data_management_plan.md'

if (-not (Test-Path $source)) { throw "Missing source: $source" }

# pandoc is not always on PATH (e.g. per-user install); fall back to the
# default per-user location before giving up.
$pandoc = (Get-Command pandoc -ErrorAction SilentlyContinue).Source
if (-not $pandoc) {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'Pandoc\pandoc.exe'),
        (Join-Path $env:ProgramFiles 'Pandoc\pandoc.exe')
    )
    $pandoc = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $pandoc) { throw "pandoc not found. Install it from https://pandoc.org/installing.html" }

$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("dmpbuild-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp -Force | Out-Null

try {
    # Strip the YAML front matter; the PDF gets its own title block below.
    $c = Get-Content -Raw -Encoding UTF8 $source
    $c = [regex]::Replace($c, '(?s)^---\r?\n.*?\r?\n---\r?\n', '')

    $combined = Join-Path $tmp 'combined.md'
    # Prepend metadata so pandoc emits a title block before the table of contents.
    $yaml = @"
---
title: "Data Management Plan"
subtitle: "InProSSA -- Industrial Problem Solving using Symbolic and Subsymbolic AI"
date: "Version 1.2 -- 29 October 2026"
---

"@
    [System.IO.File]::WriteAllText($combined, $yaml + $c.Trim() + "`n", (New-Object System.Text.UTF8Encoding $false))

    $header = @'
\usepackage{fancyhdr}
\usepackage{lastpage}
\usepackage{xcolor}
\usepackage{longtable,booktabs,array}
\usepackage{etoolbox}
% Allow hyphenation/breaking inside \texttt so long repository paths wrap
% instead of running past the right margin.
\usepackage[htt]{hyphenat}
\definecolor{inprossa}{RGB}{0,84,140}
% The data inventory tables are wide: use a smaller font and tighter column
% padding so they fit the text block.
\AtBeginEnvironment{longtable}{\footnotesize\setlength{\tabcolsep}{4pt}}
\setlength{\emergencystretch}{3em}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\footnotesize\textcolor{inprossa}{InProSSA -- Industrial Problem Solving using Symbolic and Subsymbolic AI}}
\fancyhead[R]{\footnotesize\textcolor{inprossa}{FFG FO999923579}}
\fancyfoot[L]{\footnotesize Data Management Plan -- WP1}
\fancyfoot[R]{\footnotesize Page \thepage\ of \pageref{LastPage}}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\footrulewidth}{0.4pt}
\setlength{\headheight}{14pt}
% Keep the running header/footer on the title page as well.
\fancypagestyle{plain}{%
  \fancyhf{}%
  \fancyhead[L]{\footnotesize\textcolor{inprossa}{InProSSA -- Industrial Problem Solving using Symbolic and Subsymbolic AI}}%
  \fancyhead[R]{\footnotesize\textcolor{inprossa}{FFG FO999923579}}%
  \fancyfoot[L]{\footnotesize Data Management Plan -- WP1}%
  \fancyfoot[R]{\footnotesize Page \thepage\ of \pageref{LastPage}}%
  \renewcommand{\headrulewidth}{0.4pt}%
  \renewcommand{\footrulewidth}{0.4pt}%
}
'@
    $headerFile = Join-Path $tmp 'header.tex'
    [System.IO.File]::WriteAllText($headerFile, $header, (New-Object System.Text.UTF8Encoding $false))

    & $pandoc $combined -o $out `
        --pdf-engine=xelatex `
        -V mainfont="Liberation Sans" `
        -V monofont="Liberation Mono" `
        -V sansfont="Liberation Sans" `
        -V fontsize=10pt `
        -V geometry:"a4paper,margin=2.2cm" `
        -V colorlinks=true `
        -V linkcolor=inprossa `
        -V urlcolor=inprossa `
        -V documentclass=article `
        -V lang=en-GB `
        -H $headerFile `
        --toc --toc-depth=2 -V toc-title="Contents"

    if ($LASTEXITCODE -ne 0) { throw "pandoc failed with exit code $LASTEXITCODE" }
    Write-Host "Wrote $out"
}
finally {
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}
