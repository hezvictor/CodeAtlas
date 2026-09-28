param([switch]$BuildOnly, [string[]]$Services = @('backend', 'worker', 'frontend', 'minio'))
$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskContextRoot = Join-Path $taskRoot '.build-context'
New-Item -ItemType Directory -Path $taskContextRoot -Force | Out-Null

function Copy-SourceTree([string]$Source, [string]$Destination) {
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    foreach ($entry in Get-ChildItem -LiteralPath $Source -Force) {
        if ($entry.Name -in @('__pycache__', '.pytest_cache', '.ruff_cache', '.venv', 'node_modules', '.next')) { continue }
        $target = Join-Path $Destination $entry.Name
        if ($entry.PSIsContainer) { Copy-SourceTree $entry.FullName $target }
        elseif ($entry.Extension -ne '.pyc') { Copy-Item -LiteralPath $entry.FullName -Destination $target -Force }
    }
}

foreach ($service in @('backend', 'frontend')) {
    $destination = [IO.Path]::GetFullPath((Join-Path $taskContextRoot $service))
    if (!$destination.StartsWith($taskContextRoot + [IO.Path]::DirectorySeparatorChar)) { throw 'Build context outside workspace' }
    if (Test-Path -LiteralPath $destination) { Remove-Item -LiteralPath $destination -Recurse -Force }
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    $source = Join-Path $taskRoot $service
    if ($service -eq 'backend') {
        $directories = @('app', 'migrations', 'tests')
        $files = @('Dockerfile', 'Dockerfile.test', '.dockerignore', 'pyproject.toml', 'uv.lock', 'alembic.ini')
    } else {
        $directories = @('src', 'public')
        $files = @('Dockerfile', '.dockerignore', 'package.json', 'package-lock.json', 'tsconfig.json', 'next-env.d.ts', 'next.config.ts', 'next.config.js', 'next.config.mjs', 'eslint.config.mjs', 'postcss.config.mjs', 'postcss.config.js')
    }
    foreach ($directory in $directories) { Copy-SourceTree (Join-Path $source $directory) (Join-Path $destination $directory) }
    foreach ($file in $files) { $path = Join-Path $source $file; if (Test-Path -LiteralPath $path) { Copy-Item -LiteralPath $path -Destination (Join-Path $destination $file) -Force } }
}
$backendContext = (Join-Path $taskContextRoot 'backend').Replace('\', '/')
$frontendContext = (Join-Path $taskContextRoot 'frontend').Replace('\', '/')
$override = Join-Path $taskContextRoot 'compose.build.yml'
[IO.File]::WriteAllText($override, "services:`n  backend:`n    build:`n      context: '$backendContext'`n  worker:`n    build:`n      context: '$backendContext'`n  backend-test:`n    build:`n      context: '$backendContext'`n  frontend:`n    build:`n      context: '$frontendContext'`n", [Text.UTF8Encoding]::new($false))
$compose = @('--project-directory', $taskRoot, '--env-file', (Join-Path $taskRoot '.env'), '-f', (Join-Path $taskRoot 'docker-compose.yml'), '-f', $override)
docker compose @compose build @Services
if ($LASTEXITCODE -ne 0) { throw 'Docker image build failed' }
if (!$BuildOnly) {
    docker compose @compose up -d --no-build
    if ($LASTEXITCODE -ne 0) { throw 'Docker service startup failed' }
    docker compose @compose ps
}
