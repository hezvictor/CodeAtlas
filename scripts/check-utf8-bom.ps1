$ErrorActionPreference = "Stop"

# 暂存文件编码检查，用于阻止“把 UTF-8 当 GBK 读写”造成的乱码提交。
# 1) 文本文件必须是合法 UTF-8；
# 2) 不能出现替换字符、私用区字符，或整段可被 GBK 还原成中文的乱码；
# 3) 含非 ASCII 的源码/文档必须带 UTF-8 BOM，避免 Windows 工具按 ANSI 误读。
$strictUtf8 = New-Object System.Text.UTF8Encoding($false, $true)
$lenientUtf8 = New-Object System.Text.UTF8Encoding($false, $false)
$gbk = [Text.Encoding]::GetEncoding(936)
$sourceExtensions = @(".py", ".ts", ".tsx", ".css", ".md", ".ps1", ".html", ".sh")
$textExtensions = $sourceExtensions + @(".yml", ".yaml", ".toml", ".ini", ".xml", ".env", ".txt")
$bomExemptNames = @("package.json", "package-lock.json", "tsconfig.json", ".prettierrc.json")

function Test-Mojibake {
    param([string]$text)

    $runs = [regex]::Matches($text, '[^\x00-\x7F?]+')
    if ($runs.Count -eq 0) { return $false }

    $suspicious = 0
    foreach ($run in $runs) {
        # 把疑似乱码重新按 GBK 编码后再按 UTF-8 解析；能还原出中文说明原文件被错误转码过。
        $decoded = $lenientUtf8.GetString($gbk.GetBytes($run.Value))
        $broken = ([regex]::Matches($decoded, [char]0xFFFD)).Count
        $chinese = ([regex]::Matches($decoded, '[\u4e00-\u9fff]')).Count
        if ($chinese -ge 2 -and $broken -le 1) { $suspicious++ }
    }

    return ($suspicious -ge 1 -and $suspicious * 2 -ge $runs.Count)
}

$root = git rev-parse --show-toplevel
$staged = git diff --cached --name-only --diff-filter=ACMR
$notUtf8 = @()
$mojibake = @()
$missingBom = @()

foreach ($relativePath in $staged) {
    $path = Join-Path $root $relativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { continue }

    $extension = [IO.Path]::GetExtension($path).ToLowerInvariant()
    if ($textExtensions -notcontains $extension) { continue }
    if ($bomExemptNames -contains [IO.Path]::GetFileName($path)) { continue }

    $bytes = [IO.File]::ReadAllBytes($path)
    $hasBom = ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)
    if ($hasBom -and $bytes.Length -eq 3) { $payload = @() } elseif ($hasBom) { $payload = $bytes[3..($bytes.Length - 1)] } else { $payload = $bytes }
    if (@($payload).Count -eq 0) { continue }

    try {
        $text = $strictUtf8.GetString($payload)
    } catch {
        $notUtf8 += $relativePath
        continue
    }

    if ($text.IndexOf([char]0xFFFD) -ge 0 -or $text -match '[\uE000-\uF8FF]' -or (Test-Mojibake $text)) {
        $mojibake += $relativePath
        continue
    }

    if (($sourceExtensions -contains $extension) -and -not $hasBom -and $text -match '[^\x00-\x7F]') {
        $missingBom += $relativePath
    }
}

$failed = $false

if ($notUtf8.Count -gt 0) {
    $failed = $true
    Write-Error ("以下暂存文件不是合法的 UTF-8 编码:`n" + ($notUtf8 -join "`n"))
}

if ($mojibake.Count -gt 0) {
    $failed = $true
    Write-Error ("以下暂存文件包含乱码字符（疑似 UTF-8 被按 GBK 读写）:`n" + ($mojibake -join "`n"))
}

if ($missingBom.Count -gt 0) {
    $failed = $true
    Write-Error ("以下暂存文件含非 ASCII 字符，必须以 UTF-8 BOM 保存:`n" + ($missingBom -join "`n"))
}

if ($failed) { exit 1 }

Write-Host "暂存文件编码检查通过。"
