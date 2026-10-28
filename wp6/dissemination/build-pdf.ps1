#!/usr/bin/env pwsh
# Builds wp6/dissemination/InProSSA_Dissemination_Plan.pdf from the Markdown sources.
# Requires: pandoc (>= 3.x) and a LaTeX engine (xelatex) on PATH.
#
# Usage:  pwsh wp6/dissemination/build-pdf.ps1

$ErrorActionPreference = 'Stop'

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$out = Join-Path $here 'InProSSA_Dissemination_Plan.pdf'
$cslFile = Join-Path $here 'ieee.csl'

$sources = @(
    (Join-Path $here 'dissemination.md'),
    (Join-Path $here 'follow_up.md')
)

foreach ($s in $sources) {
    if (-not (Test-Path $s)) { throw "Missing source: $s" }
}

$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("dissbuild-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp -Force | Out-Null

try {
    # Concatenate the sources, dropping the YAML front matter and the per-file
    # footer (the footer is reproduced once in the PDF page footer instead).
    $sb = New-Object System.Text.StringBuilder
    $first = $true
    foreach ($s in $sources) {
        $c = Get-Content -Raw -Encoding UTF8 $s
        $c = [regex]::Replace($c, '(?s)^---\r?\n.*?\r?\n---\r?\n', '')
        $c = [regex]::Replace($c, '(?s)\r?\n---\r?\n\*InProSSA.*?CC BY 4\.0\.\*\s*$', '')
        # Cross-file links become intra-document anchors, and the link text
        # becomes the section name rather than the source file name.
        $c = $c -replace '\[follow_up\.md\]\([^)]*\)', '[Follow-up research strategies and exploitation](#follow-up-research-strategies-and-exploitation)'
        $c = $c -replace '\[references\.bib\]\([^)]*\)', '[Appendix: Bibliography](#appendix-bibliography)'
        if (-not $first) {
            [void]$sb.AppendLine()
            [void]$sb.AppendLine('```{=latex}')
            [void]$sb.AppendLine('\newpage')
            [void]$sb.AppendLine('```')
            [void]$sb.AppendLine()
        }
        [void]$sb.AppendLine($c.Trim())
        $first = $false
    }
    $combined = Join-Path $tmp 'combined.md'
    # Prepend metadata so citeproc includes every entry in the bibliography and
    # pandoc emits a title block before the table of contents.
    $yaml = @"
---
title: "Dissemination Plan"
subtitle: "InProSSA -- Industrial Problem Solving using Symbolic and Subsymbolic AI"
nocite: '@*'
---

"@
    [System.IO.File]::WriteAllText($combined, $yaml + $sb.ToString(), (New-Object System.Text.UTF8Encoding $false))

    # Appendix: the bibliography rendered from references.bib via pandoc's
    # citeproc, so entries appear in a citation style (with DOIs/URLs) rather
    # than as raw BibTeX.
    $bibFile = Join-Path $here 'references.bib'
    if (Test-Path $bibFile) {
        $appendix = @"

``````{=latex}
\newpage
\appendix
``````

# Appendix: Bibliography

::: {#refs}
:::

"@
        Add-Content -Path $combined -Value $appendix -Encoding UTF8
    }
    else {
        Write-Warning "references.bib not found; appendix omitted."
    }

    $header = @'
\usepackage{fancyhdr}
\usepackage{lastpage}
\usepackage{xcolor}
\definecolor{inprossa}{RGB}{0,84,140}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\footnotesize\textcolor{inprossa}{InProSSA -- Industrial Problem Solving using Symbolic and Subsymbolic AI}}
\fancyhead[R]{\footnotesize\textcolor{inprossa}{FFG FO999923579}}
\fancyfoot[L]{\footnotesize Dissemination Plan -- WP6}
\fancyfoot[R]{\footnotesize Page \thepage\ of \pageref{LastPage}}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\footrulewidth}{0.4pt}
\setlength{\headheight}{14pt}
% Keep the running header/footer on the title page as well.
\fancypagestyle{plain}{%
  \fancyhf{}%
  \fancyhead[L]{\footnotesize\textcolor{inprossa}{InProSSA -- Industrial Problem Solving using Symbolic and Subsymbolic AI}}%
  \fancyhead[R]{\footnotesize\textcolor{inprossa}{FFG FO999923579}}%
  \fancyfoot[L]{\footnotesize Dissemination Plan -- WP6}%
  \fancyfoot[R]{\footnotesize Page \thepage\ of \pageref{LastPage}}%
  \renewcommand{\headrulewidth}{0.4pt}%
  \renewcommand{\footrulewidth}{0.4pt}%
}
'@
    $headerFile = Join-Path $tmp 'header.tex'
    [System.IO.File]::WriteAllText($headerFile, $header, (New-Object System.Text.UTF8Encoding $false))

    pandoc $combined -o $out `
        --pdf-engine=xelatex `
        --citeproc `
        --bibliography=$bibFile `
        --csl=$cslFile `
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
