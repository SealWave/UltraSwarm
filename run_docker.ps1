# UltraSwarm Docker Run Script for Windows PowerShell
# Cross-platform Docker execution

param(
    [Parameter(Position=0)]
    [ValidateSet("build", "run", "compose", "agent", "swarm", "logs", "stop", "shell", "clean", "help")]
    [string]$Command = "run",
    
    [Parameter(Position=1)]
    [string]$Name = ""
)

# Colors
$Red = "`e[31m"
$Green = "`e[32m"
$Yellow = "`e[33m"
$Blue = "`e[34m"
$Reset = "`e[0m"

function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Test-Docker {
    try {
        docker info | Out-Null
        Write-ColorOutput $Green "✓ Docker is available and running"
        return $true
    }
    catch {
        Write-ColorOutput $Red "Error: Docker is not installed or not running."
        Write-ColorOutput $Yellow "Please install Docker Desktop from: https://docs.docker.com/desktop/install/windows-install/"
        return $false
    }
}

function Test-EnvFile {
    if (-not (Test-Path ".env")) {
        Write-ColorOutput $Yellow "Warning: .env file not found."
        
        if (Test-Path ".env.example") {
            Write-ColorOutput $Blue "Creating .env from .env.example..."
            Copy-Item ".env.example" ".env"
            Write-ColorOutput $Yellow "Please edit .env and add your API keys."
        }
        else {
            Write-ColorOutput $Blue "Creating minimal .env file..."
            @"
# UltraSwarm Configuration
GOOGLE_API_KEY=your_api_key_here

# Browser Settings
BROWSER_HEADLESS=true
BROWSER_USE_AUTO_START=true

# Playwright (Arch Linux compatibility - for WSL)
PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1
"@ | Out-File -FilePath ".env" -Encoding utf8
            Write-ColorOutput $Yellow "Please edit .env and add your API keys."
        }
        return $false
    }
    
    Write-ColorOutput $Green "✓ .env file found"
    return $true
}

function Build-Image {
    Write-ColorOutput $Blue "Building UltraSwarm Docker image..."
    
    docker build `
        --build-arg TARGETPLATFORM=linux/amd64 `
        --build-arg BUILDPLATFORM=linux/amd64 `
        -t ultraswarm:latest `
        -t "ultraswarm:$(Get-Date -Format 'yyyyMMdd')" `
        .
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput $Green "✓ Docker image built successfully"
    }
}

function Start-Interactive {
    Write-ColorOutput $Blue "Starting UltraSwarm in interactive mode..."
    
    $envContent = Get-Content ".env" | Where-Object { $_ -match "GOOGLE_API_KEY" }
    $apiKey = ($envContent -split "=")[1]
    
    docker run -it --rm `
        --name ultraswarm-interactive `
        -e "GOOGLE_API_KEY=$apiKey" `
        -e BROWSER_HEADLESS=true `
        -e PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1 `
        -v "${PWD}/outputs:/app/outputs" `
        -v "${PWD}/knowledge:/app/knowledge" `
        ultraswarm:latest
}

function Start-Compose {
    Write-ColorOutput $Blue "Starting UltraSwarm with Docker Compose..."
    
    docker-compose up -d
    
    Write-ColorOutput $Green "✓ UltraSwarm started in background"
    Write-ColorOutput $Blue "View logs: docker-compose logs -f"
    Write-ColorOutput $Blue "Stop: docker-compose down"
}

function Start-Agent {
    param([string]$AgentName)
    
    Write-ColorOutput $Blue "Running agent: $AgentName"
    
    $envContent = Get-Content ".env" | Where-Object { $_ -match "GOOGLE_API_KEY" }
    $apiKey = ($envContent -split "=")[1]
    
    docker run -it --rm `
        --name "ultraswarm-$AgentName" `
        -e "GOOGLE_API_KEY=$apiKey" `
        -e BROWSER_HEADLESS=true `
        -e PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1 `
        -v "${PWD}/outputs:/app/outputs" `
        ultraswarm:latest `
        python main.py --agent $AgentName
}

function Start-Swarm {
    param([string]$SwarmName)
    
    Write-ColorOutput $Blue "Running swarm: $SwarmName"
    
    $envContent = Get-Content ".env" | Where-Object { $_ -match "GOOGLE_API_KEY" }
    $apiKey = ($envContent -split "=")[1]
    
    docker run -it --rm `
        --name "ultraswarm-$SwarmName" `
        -e "GOOGLE_API_KEY=$apiKey" `
        -e BROWSER_HEADLESS=true `
        -e PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1 `
        -v "${PWD}/outputs:/app/outputs" `
        ultraswarm:latest `
        python main.py --swarm $SwarmName
}

function Show-Help {
    Write-Output "UltraSwarm Docker Runner"
    Write-Output ""
    Write-Output "Usage: .\run_docker.ps1 [command] [name]"
    Write-Output ""
    Write-Output "Commands:"
    Write-Output "  build        Build Docker image"
    Write-Output "  run          Run interactive mode (default)"
    Write-Output "  compose      Run with docker-compose"
    Write-Output "  agent NAME   Run specific agent"
    Write-Output "  swarm NAME   Run specific swarm"
    Write-Output "  logs         View container logs"
    Write-Output "  stop         Stop running containers"
    Write-Output "  shell        Open shell in container"
    Write-Output "  clean        Remove containers and images"
    Write-Output ""
    Write-Output "Examples:"
    Write-Output "  .\run_docker.ps1 build"
    Write-Output "  .\run_docker.ps1 run"
    Write-Output "  .\run_docker.ps1 agent seo"
    Write-Output "  .\run_docker.ps1 swarm full"
}

# Main execution
Write-ColorOutput $Blue "🐝 UltraSwarm Docker Runner"
Write-Output ""

if (-not (Test-Docker)) {
    exit 1
}

switch ($Command) {
    "build" {
        if (Test-EnvFile) {
            Build-Image
        }
    }
    "run" {
        if (Test-EnvFile) {
            Start-Interactive
        }
    }
    "compose" {
        if (Test-EnvFile) {
            Start-Compose
        }
    }
    "agent" {
        if ([string]::IsNullOrEmpty($Name)) {
            Write-ColorOutput $Red "Error: Agent name required."
            Write-Output "Available agents: seo, product, ads, social, banner, store, browser, research, email, stocks, support, tests, competitive, debate"
            exit 1
        }
        if (Test-EnvFile) {
            Start-Agent -AgentName $Name
        }
    }
    "swarm" {
        if ([string]::IsNullOrEmpty($Name)) {
            Write-ColorOutput $Red "Error: Swarm name required."
            Write-Output "Available swarms: product, marketing, seo, full"
            exit 1
        }
        if (Test-EnvFile) {
            Start-Swarm -SwarmName $Name
        }
    }
    "logs" {
        docker-compose logs -f
    }
    "stop" {
        Write-ColorOutput $Yellow "Stopping containers..."
        docker-compose down
        Write-ColorOutput $Green "✓ Containers stopped"
    }
    "shell" {
        docker run -it --rm --entrypoint /bin/bash ultraswarm:latest
    }
    "clean" {
        Write-ColorOutput $Yellow "Cleaning up..."
        docker-compose down -v --rmi local
        docker rmi ultraswarm:latest 2>$null
        Write-ColorOutput $Green "✓ Cleanup complete"
    }
    "help" {
        Show-Help
    }
}
