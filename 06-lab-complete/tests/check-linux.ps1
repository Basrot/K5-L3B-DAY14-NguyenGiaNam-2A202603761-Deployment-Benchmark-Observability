# Run the unmodified lab grader on Linux from Windows + Docker Desktop.
param([int]$RedisPort = 16380)
$ErrorActionPreference = 'Stop'
$part6Path = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$redisName = 'day14-check-' + [guid]::NewGuid().ToString('N').Substring(0, 12)
$reportPath = Join-Path $part6Path 'verification'
New-Item -ItemType Directory -Force $reportPath | Out-Null
Push-Location $part6Path
try {
    docker build -f tests/Dockerfile.checker -t day14-checker:local .
    if ($LASTEXITCODE -ne 0) { throw 'Checker image build failed' }
    # Explicit ports are reachable from both Windows and Linux host networking.
    docker run -d --name $redisName -p "127.0.0.1:${RedisPort}:6379" redis:7-alpine
    if ($LASTEXITCODE -ne 0) { throw 'Test Redis startup failed' }
    docker exec $redisName redis-cli ping
    if ($LASTEXITCODE -ne 0) { throw 'Test Redis is not ready' }
    $mount = "type=bind,source=$part6Path,target=/workspace"
    docker run --rm --network host -e "TEST_REDIS_URL=redis://127.0.0.1:$RedisPort/15" --mount $mount day14-checker:local python -m unittest discover -s tests -v *> (Join-Path $reportPath 'part6-integration.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Integration tests failed; see verification/part6-integration.txt' }
    docker run --rm --network host --mount 'type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock' --mount $mount day14-checker:local python check_production_ready.py --redis-url "redis://127.0.0.1:$RedisPort/0" *> (Join-Path $reportPath 'part6-readiness.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Readiness checks failed; see verification/part6-readiness.txt' }
    Get-Content -Encoding UTF8 (Join-Path $reportPath 'part6-readiness.txt') | Select-Object -Last 22
} finally {
    docker rm -f $redisName | Out-Null
    Pop-Location
}
