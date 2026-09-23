<#
.SYNOPSIS
    把 Markdown 导出为 PDF。在浏览器里完成渲染，除浏览器本身外不依赖任何外部程序。

.DESCRIPTION
    流水线：读 Markdown → 抽出公式占位 → 组装自包含 HTML → 浏览器无头打印为 PDF。
    渲染器（markdown-it）、公式排版（KaTeX）、主题样式全部随本 skill 携带，无需联网。
    产出默认写到 Markdown 同目录、同名 .pdf。

.PARAMETER Path
    Markdown 文件路径，或目录路径（目录则递归导出其中所有 .md）。

.PARAMETER Theme
    预览主题，对应 assets/themes/<Theme>.css。默认 github-light。

.PARAMETER Paper
    纸张。letter（默认，与 Chrome 默认一致）或 a4。

.PARAMETER Out
    输出路径。单文件时可指定；目录批量时不适用（逐个写到各自同目录）。

.PARAMETER Html
    只生成 HTML，不打印 PDF。

.EXAMPLE
    ./export.ps1 ../../docs/手册.md
.EXAMPLE
    ./export.ps1 ../学习资料 -Theme newsprint -Paper a4
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory, Position = 0)]
    [string]$Path,

    [string]$Theme = 'github-light',

    [ValidateSet('letter', 'a4')]
    [string]$Paper = 'letter',

    [string]$Out,

    [switch]$Html
)

$ErrorActionPreference = 'Stop'

$AssetRoot = Join-Path (Split-Path $PSScriptRoot -Parent) 'assets'
$ThemeFile = Join-Path $AssetRoot "themes/$Theme.css"
if (-not (Test-Path $ThemeFile)) {
    $available = (Get-ChildItem (Join-Path $AssetRoot 'themes') -Filter *.css |
        Where-Object { $_.BaseName -ne 'LICENSE-NCSA' } | ForEach-Object BaseName) -join ', '
    throw "主题不存在：$Theme`n可用主题：$available"
}

function Get-ChromiumBrowser {
    $candidates = @(
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe"
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
        "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
        "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'
        '/usr/bin/google-chrome'
        '/usr/bin/chromium'
        '/usr/bin/chromium-browser'
    )
    foreach ($c in $candidates) { if ($c -and (Test-Path $c)) { return $c } }
    foreach ($n in 'chrome', 'msedge', 'chromium', 'google-chrome') {
        $cmd = Get-Command $n -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    throw "未找到 Chromium 内核浏览器。请安装 Google Chrome 或 Microsoft Edge 后重试。"
}

function Convert-MarkdownToHtml {
    param([string]$MarkdownPath, [string]$ThemePath, [string]$PaperSize)

    $md = [System.IO.File]::ReadAllText($MarkdownPath, [System.Text.Encoding]::UTF8)

    # 公式先抽成占位符，否则公式里的 _ ^ \ 会被 Markdown 当成强调、转义语法吃掉
    $maths = [System.Collections.ArrayList]::new()
    $blockRe = [regex]::new('\$\$(.+?)\$\$', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    $md = $blockRe.Replace($md, {
            param($m)
            [void]$maths.Add(@{ tex = $m.Groups[1].Value; display = $true })
            "XMATHX$($maths.Count - 1)XMATHX"
        })
    $inlineRe = [regex]::new('(?<!\$)\$([^$\r\n]+?)\$(?!\$)')
    $md = $inlineRe.Replace($md, {
            param($m)
            [void]$maths.Add(@{ tex = $m.Groups[1].Value; display = $false })
            "XMATHX$($maths.Count - 1)XMATHX"
        })

    $themeCss = [System.IO.File]::ReadAllText($ThemePath, [System.Text.Encoding]::UTF8)
    $mditJs = [System.IO.File]::ReadAllText((Join-Path $AssetRoot 'vendor/markdown-it.min.js'), [System.Text.Encoding]::UTF8)

    $katexCssBlock = ''
    $katexJsBlock = ''
    if ($maths.Count -gt 0) {
        $katexCssBlock = '<style>' + [System.IO.File]::ReadAllText((Join-Path $AssetRoot 'vendor/katex.min.css'), [System.Text.Encoding]::UTF8) + '</style>'
        $katexJsBlock = '<script>' + [System.IO.File]::ReadAllText((Join-Path $AssetRoot 'vendor/katex.min.js'), [System.Text.Encoding]::UTF8) + '</script>'
    }

    $mathsJson = ConvertTo-Json -InputObject @($maths) -Compress -Depth 5
    if (-not $mathsJson.StartsWith('[')) { $mathsJson = "[$mathsJson]" }

    $title = [System.IO.Path]::GetFileNameWithoutExtension($MarkdownPath)
    $mdEscaped = $md.Replace('</script>', '<\/script>')

    # breaks:true 对应 MPE 的 breakOnSingleNewLine 默认值——单换行渲染为换行而非空格
    $html = @"
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>$title</title>
$katexCssBlock
<style>
$themeCss
</style>
<style>
@page { size: $PaperSize; margin: 0.4in; }
body { padding-top: 28px; }
</style>
</head>
<body>
<script type="text/markdown" id="src">$mdEscaped</script>
<script>$mditJs</script>
$katexJsBlock
<script>
const maths = $mathsJson;
const md = window.markdownit({ html: true, linkify: true, breaks: true });
let out = md.render(document.getElementById('src').textContent);
if (maths.length) {
  out = out.replace(/XMATHX(\d+)XMATHX/g, (_, i) => {
    const [tex, display] = [maths[i].tex, maths[i].display];
    try { return katex.renderToString(tex, { displayMode: display, throwOnError: false }); }
    catch (e) { return '<code>' + tex + '</code>'; }
  });
}
document.body.innerHTML = out;
document.documentElement.setAttribute('data-ready', '1');
</script>
</body>
</html>
"@
    return $html
}

function Export-One {
    param([string]$MarkdownPath, [string]$Browser, [string]$ThemePath, [string]$PaperSize, [string]$OutPath, [switch]$HtmlOnly)

    # 临时 HTML 写在 .md 同目录：这样文档里的相对图片路径能按原样解析
    $tempHtml = Join-Path (Split-Path $MarkdownPath -Parent) (".md-export-" + [guid]::NewGuid().ToString('N').Substring(0, 8) + ".html")
    $pdfPath = if ($OutPath) { $OutPath } else { [System.IO.Path]::ChangeExtension($MarkdownPath, '.pdf') }

    try {
        $html = Convert-MarkdownToHtml -MarkdownPath $MarkdownPath -ThemePath $ThemePath -PaperSize $PaperSize
        [System.IO.File]::WriteAllText($tempHtml, $html, [System.Text.UTF8Encoding]::new($false))

        if ($HtmlOnly) {
            $target = if ($OutPath) { $OutPath } else { [System.IO.Path]::ChangeExtension($MarkdownPath, '.html') }
            Move-Item -LiteralPath $tempHtml -Destination $target -Force
            return [pscustomobject]@{ File = $MarkdownPath; Output = $target; Pages = $null }
        }

        $profileDir = Join-Path ([System.IO.Path]::GetTempPath()) ("md-export-profile-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
        $url = ([uri]$tempHtml).AbsoluteUri
        $chromeArgs = @(
            '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
            "--user-data-dir=$profileDir",
            '--no-pdf-header-footer', '--virtual-time-budget=15000',
            "--print-to-pdf=$pdfPath", $url
        )
        if (Test-Path $pdfPath) { Remove-Item -LiteralPath $pdfPath -Force }
        & $Browser @chromeArgs 2>&1 | Out-Null
        Remove-Item -LiteralPath $profileDir -Recurse -Force -ErrorAction SilentlyContinue

        if (-not (Test-Path $pdfPath)) { throw "打印失败，未产出 PDF：$pdfPath" }

        return [pscustomobject]@{ File = $MarkdownPath; Output = $pdfPath; Pages = (Get-PdfPageCount $pdfPath) }
    }
    finally {
        if (Test-Path $tempHtml) { Remove-Item -LiteralPath $tempHtml -Force -ErrorAction SilentlyContinue }
    }
}

function Get-PdfPageCount {
    param([string]$PdfPath)
    try {
        $bytes = [System.IO.File]::ReadAllBytes($PdfPath)
        $text = [System.Text.Encoding]::GetEncoding(28591).GetString($bytes)
        $counts = [regex]::Matches($text, '/Type\s*/Page[^s]') | Measure-Object
        if ($counts.Count -gt 0) { return $counts.Count }
    }
    catch { }
    return $null
}

# ---- 主流程 ----
$resolved = (Resolve-Path -LiteralPath $Path).ProviderPath
$targets = @()
$isBatch = $false

if (Test-Path -LiteralPath $resolved -PathType Container) {
    $isBatch = $true
    $targets = Get-ChildItem -LiteralPath $resolved -Filter *.md -Recurse -File |
        Where-Object { $_.Name -notlike '.md-export-*' } | Sort-Object FullName
    if ($targets.Count -eq 0) { throw "目录下没有 .md 文件：$resolved" }
}
else {
    $targets = @(Get-Item -LiteralPath $resolved)
}

$browser = if ($Html) { $null } else { Get-ChromiumBrowser }
$results = @()

foreach ($t in $targets) {
    $one = if ($isBatch) { $null } else { $Out }
    try {
        $r = Export-One -MarkdownPath $t.FullName -Browser $browser -ThemePath $ThemeFile -PaperSize $Paper -OutPath $one -HtmlOnly:$Html
        $results += $r
        $rel = if ($isBatch) { $t.FullName.Substring($resolved.Length).TrimStart('\', '/') } else { $t.Name }
        $pages = if ($r.Pages) { "$($r.Pages) 页" } else { '' }
        Write-Host "  ✓ $rel  $pages"
    }
    catch {
        Write-Host "  ✗ $($t.Name)  $($_.Exception.Message)" -ForegroundColor Red
    }
}

$ok = ($results | Measure-Object).Count
$unit = if ($Html) { 'HTML' } else { 'PDF' }
Write-Host ""
Write-Host "完成：$ok / $($targets.Count) 个文件已导出为 $unit（主题 $Theme，纸张 $Paper）"
if ($isBatch) {
    Write-Host "输出目录：$resolved"
}
elseif ($results.Count -gt 0) {
    Write-Host "输出文件：$($results[0].Output)"
}
