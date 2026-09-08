$ErrorActionPreference = "Stop"

$root = git rev-parse --show-toplevel
$tracked = git diff --cached --name-only --diff-filter=ACMR
$extensions = @(".py", ".ts", ".tsx", ".css", ".md", ".yml", ".yaml", ".toml", ".ini", ".html", ".xml", ".env", ".ps1")
$errors = @()

foreach ($relativePath in $tracked) {
    $path = Join-Path $root $relativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { continue }
    if ($extensions -notcontains [IO.Path]::GetExtension($path).ToLowerInvariant()) { continue }; if ([IO.Path]::GetFileName($path) -in @("package.json", "package-lock.json", "tsconfig.json", ".prettierrc.json")) { continue }

    $bytes = [IO.File]::ReadAllBytes($path)
    if ($bytes.Length -lt 3 -or $bytes[0] -ne 0xEF -or $bytes[1] -ne 0xBB -or $bytes[2] -ne 0xBF) {
        $errors += $relativePath
    }
}

if ($errors.Count -gt 0) {
    Write-Error ("这些暂存文件不是 UTF-8 BOM 编码:`n" + ($errors -join "`n"))
    exit 1
}

Write-Host "UTF-8 BOM 编码检查通过。"
