# Redis Service Manager for Windows
# This script checks if Redis is running and starts it if needed

param(
    [switch]$Force,
    [switch]$Verbose
)

# Configuration
$RedisServiceName = "Redis"
$RedisExecutable = "redis-server.exe"
$RedisPort = 6379

Write-Host "Redis Service Manager" -ForegroundColor Green
Write-Host "===================" -ForegroundColor Green

function Test-RedisConnection {
    param([int]$Port = 6379)
    
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $result = $tcpClient.BeginConnect("localhost", $Port, $null, $null)
        $success = $result.AsyncWaitHandle.WaitOne(1000, $false)
        $tcpClient.Close()
        return $success
    }
    catch {
        return $false
    }
}

function Get-RedisProcess {
    return Get-Process -Name "redis-server" -ErrorAction SilentlyContinue
}

function Get-RedisService {
    return Get-Service -Name $RedisServiceName -ErrorAction SilentlyContinue
}

function Start-RedisService {
    $service = Get-RedisService
    if ($service) {
        Write-Host "Starting Redis service..." -ForegroundColor Yellow
        try {
            Start-Service -Name $RedisServiceName
            Start-Sleep -Seconds 3
            return $true
        }
        catch {
            Write-Host "Failed to start Redis service: $($_.Exception.Message)" -ForegroundColor Red
            return $false
        }
    }
    return $false
}

function Start-RedisExecutable {
    Write-Host "Attempting to start Redis executable..." -ForegroundColor Yellow
    
    # Common Redis installation paths
    $redisPaths = @(
        "C:\Program Files\Redis\redis-server.exe",
        "C:\Redis\redis-server.exe",
        "C:\tools\redis\redis-server.exe",
        "${env:ProgramFiles}\Redis\redis-server.exe",
        "${env:ProgramFiles(x86)}\Redis\redis-server.exe"
    )
    
    # Check if redis-server is in PATH
    $redisInPath = Get-Command "redis-server" -ErrorAction SilentlyContinue
    if ($redisInPath) {
        try {
            Start-Process -FilePath "redis-server" -WindowStyle Minimized
            Start-Sleep -Seconds 3
            return $true
        }
        catch {
            Write-Host "Failed to start redis-server from PATH: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    # Try common installation paths
    foreach ($path in $redisPaths) {
        if (Test-Path $path) {
            try {
                Write-Host "Found Redis at: $path" -ForegroundColor Cyan
                Start-Process -FilePath $path -WindowStyle Minimized
                Start-Sleep -Seconds 3
                return $true
            }
            catch {
                Write-Host "Failed to start Redis from $path : $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }
    
    return $false
}

# Main logic
Write-Host "Checking Redis status..." -ForegroundColor Cyan

# Check if Redis is already running
$redisProcess = Get-RedisProcess
$redisConnectable = Test-RedisConnection -Port $RedisPort

if ($redisProcess -and $redisConnectable) {
    Write-Host "[OK] Redis is already running (PID: $($redisProcess.Id), Port: $RedisPort)" -ForegroundColor Green
    if ($Verbose) {
        Write-Host "Process details:" -ForegroundColor Gray
        $redisProcess | Select-Object Id, ProcessName, StartTime, WorkingSet | Format-Table
    }
    exit 0
}

if ($Force -or -not $redisConnectable) {
    Write-Host "Redis is not running. Attempting to start..." -ForegroundColor Yellow
    
    # Try to start as Windows service first
    $serviceStarted = Start-RedisService
    
    if ($serviceStarted) {
        Start-Sleep -Seconds 2
        if (Test-RedisConnection -Port $RedisPort) {
            Write-Host "[OK] Redis service started successfully!" -ForegroundColor Green
            exit 0
        }
    }
    
    # If service method failed, try executable
    $executableStarted = Start-RedisExecutable
    
    if ($executableStarted) {
        Start-Sleep -Seconds 2
        if (Test-RedisConnection -Port $RedisPort) {
            Write-Host "[OK] Redis started successfully via executable!" -ForegroundColor Green
            exit 0
        }
    }
    
    # Final check
    if (Test-RedisConnection -Port $RedisPort) {
        Write-Host "[OK] Redis is now running on port $RedisPort" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "Failed to start Redis. Please check:" -ForegroundColor Red
        Write-Host "  1. Redis is installed" -ForegroundColor Yellow
        Write-Host "  2. Redis service is configured" -ForegroundColor Yellow
        Write-Host "  3. Port $RedisPort is not blocked by firewall" -ForegroundColor Yellow
        Write-Host "  4. You have sufficient permissions" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "Redis connection test passed" -ForegroundColor Green
}
