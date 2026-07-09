#!/bin/bash
# UltraSwarm Docker Run Script
# Cross-platform Docker execution for Windows (WSL/Git Bash) and Linux

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_msg() {
    echo -e "${2}${1}${NC}"
}

# Detect platform
detect_platform() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_msg "Error: Docker is not installed." "$RED"
        print_msg "Please install Docker from: https://docs.docker.com/get-docker/" "$YELLOW"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_msg "Error: Docker daemon is not running." "$RED"
        print_msg "Please start Docker and try again." "$YELLOW"
        exit 1
    fi
    
    print_msg "✓ Docker is available and running" "$GREEN"
}

# Check for .env file
check_env() {
    if [[ ! -f ".env" ]]; then
        print_msg "Warning: .env file not found." "$YELLOW"
        
        if [[ -f ".env.example" ]]; then
            print_msg "Creating .env from .env.example..." "$BLUE"
            cp .env.example .env
            print_msg "Please edit .env and add your API keys." "$YELLOW"
        else
            print_msg "Creating minimal .env file..." "$BLUE"
            cat > .env << EOF
# UltraSwarm Configuration
GOOGLE_API_KEY=your_api_key_here

# Browser Settings
BROWSER_HEADLESS=true
BROWSER_USE_AUTO_START=true

# Playwright (Arch Linux compatibility)
PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1
EOF
            print_msg "Please edit .env and add your API keys." "$YELLOW"
        fi
        
        exit 1
    fi
    
    print_msg "✓ .env file found" "$GREEN"
}

# Build Docker image
build_image() {
    print_msg "Building UltraSwarm Docker image..." "$BLUE"
    
    docker build \
        --build-arg TARGETPLATFORM=linux/amd64 \
        --build-arg BUILDPLATFORM=linux/amd64 \
        -t ultraswarm:latest \
        -t ultraswarm:$(date +%Y%m%d) \
        .
    
    print_msg "✓ Docker image built successfully" "$GREEN"
}

# Run container interactively
run_interactive() {
    print_msg "Starting UltraSwarm in interactive mode..." "$BLUE"
    
    docker run -it --rm \
        --name ultraswarm-interactive \
        -e GOOGLE_API_KEY="${GOOGLE_API_KEY:-$(grep GOOGLE_API_KEY .env | cut -d'=' -f2)}" \
        -e BROWSER_HEADLESS=true \
        -e PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1 \
        -v "$(pwd)/outputs:/app/outputs" \
        -v "$(pwd)/knowledge:/app/knowledge" \
        ultraswarm:latest
}

# Run with docker-compose
run_compose() {
    print_msg "Starting UltraSwarm with Docker Compose..." "$BLUE"
    
    docker-compose up -d
    
    print_msg "✓ UltraSwarm started in background" "$GREEN"
    print_msg "View logs: docker-compose logs -f" "$BLUE"
    print_msg "Stop: docker-compose down" "$BLUE"
}

# Run specific agent
run_agent() {
    local agent=$1
    print_msg "Running agent: $agent" "$BLUE"
    
    docker run -it --rm \
        --name ultraswarm-"$agent" \
        -e GOOGLE_API_KEY="${GOOGLE_API_KEY:-$(grep GOOGLE_API_KEY .env | cut -d'=' -f2)}" \
        -e BROWSER_HEADLESS=true \
        -e PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1 \
        -v "$(pwd)/outputs:/app/outputs" \
        ultraswarm:latest \
        python main.py --agent "$agent"
}

# Run swarm
run_swarm() {
    local swarm=$1
    print_msg "Running swarm: $swarm" "$BLUE"
    
    docker run -it --rm \
        --name ultraswarm-"$swarm" \
        -e GOOGLE_API_KEY="${GOOGLE_API_KEY:-$(grep GOOGLE_API_KEY .env | cut -d'=' -f2)}" \
        -e BROWSER_HEADLESS=true \
        -e PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1 \
        -v "$(pwd)/outputs:/app/outputs" \
        ultraswarm:latest \
        python main.py --swarm "$swarm"
}

# Show usage
show_usage() {
    echo "UltraSwarm Docker Runner"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  build        Build Docker image"
    echo "  run          Run interactive mode (default)"
    echo "  compose      Run with docker-compose"
    echo "  agent NAME   Run specific agent (seo, product, ads, social, etc.)"
    echo "  swarm NAME   Run specific swarm (product, marketing, seo, full)"
    echo "  logs         View container logs"
    echo "  stop         Stop running containers"
    echo "  shell        Open shell in container"
    echo "  clean        Remove containers and images"
    echo ""
    echo "Examples:"
    echo "  $0 build"
    echo "  $0 run"
    echo "  $0 agent seo"
    echo "  $0 swarm full"
}

# Main script
main() {
    print_msg "🐝 UltraSwarm Docker Runner" "$BLUE"
    echo ""
    
    # Change to script directory
    cd "$(dirname "$0")"
    
    # Check prerequisites
    check_docker
    
    case "${1:-run}" in
        build)
            check_env
            build_image
            ;;
        run)
            check_env
            run_interactive
            ;;
        compose)
            check_env
            run_compose
            ;;
        agent)
            if [[ -z "$2" ]]; then
                print_msg "Error: Agent name required." "$RED"
                echo "Available agents: seo, product, ads, social, banner, store, browser, research, email, stocks, support, tests, competitive, debate"
                exit 1
            fi
            check_env
            run_agent "$2"
            ;;
        swarm)
            if [[ -z "$2" ]]; then
                print_msg "Error: Swarm name required." "$RED"
                echo "Available swarms: product, marketing, seo, full"
                exit 1
            fi
            check_env
            run_swarm "$2"
            ;;
        logs)
            docker-compose logs -f
            ;;
        stop)
            print_msg "Stopping containers..." "$YELLOW"
            docker-compose down
            print_msg "✓ Containers stopped" "$GREEN"
            ;;
        shell)
            docker run -it --rm --entrypoint /bin/bash ultraswarm:latest
            ;;
        clean)
            print_msg "Cleaning up..." "$YELLOW"
            docker-compose down -v --rmi local
            docker rmi ultraswarm:latest 2>/dev/null || true
            print_msg "✓ Cleanup complete" "$GREEN"
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            print_msg "Unknown command: $1" "$RED"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
