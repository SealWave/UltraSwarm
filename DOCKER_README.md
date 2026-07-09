# Docker Guide for UltraSwarm

This document explains how to run UltraSwarm using Docker on Windows and Linux (including Arch Linux).

## Quick Start

### Prerequisites

- Docker Desktop (Windows/macOS) or Docker Engine (Linux)
- Docker Compose (included in Docker Desktop)

### Running UltraSwarm

#### Option 1: Interactive Mode

```bash
# Linux/macOS
./run_docker.sh run

# Windows (PowerShell)
.\run_docker.ps1 run
```

#### Option 2: Docker Compose

```bash
docker-compose up
```

#### Option 3: Direct Docker Run

```bash
docker run -it --rm \
  -e GOOGLE_API_KEY=your_key \
  -e BROWSER_HEADLESS=true \
  -v $(pwd)/outputs:/app/outputs \
  ultraswarm:latest
```

## Platform-Specific Instructions

### Windows

1. **Install Docker Desktop**
   - Download from: https://docs.docker.com/desktop/install/windows-install/
   - Enable WSL 2 backend for better Linux compatibility

2. **Run UltraSwarm**
   ```bash
   # Using PowerShell script
   .\run_docker.ps1 run
   
   # Using Docker Compose
   docker-compose up
   ```

3. **WSL 2 Notes**
   - UltraSwarm works in WSL 2 with Windows Docker Desktop
   - Browser automation uses Docker's built-in Chrome

### Linux

#### Standard Distributions (Ubuntu, Debian, Fedora)

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Run UltraSwarm
./run_docker.sh run
```

#### Arch Linux

UltraSwarm includes special handling for Arch Linux's rolling release model:

```bash
# Arch Linux with Docker
./run_docker.sh run

# Or with podman (alternative to Docker)
podman run -it --rm \
  -e GOOGLE_API_KEY=your_key \
  -e BROWSER_HEADLESS=true \
  -v $(pwd)/outputs:/app/outputs \
  ultraswarm:latest
```

**Arch Linux specific configurations:**
- `PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1` - Skips system library validation
- Disables VizDisplayCompositor which can cause issues on Arch
- Uses Playwright's bundled Chromium instead of system packages

### macOS

```bash
# Install Docker Desktop for Mac
# Then run:
./run_docker.sh run
```

## Docker Compose Usage

Docker Compose is the recommended way to run UltraSwarm with persistent storage and easier configuration.

### Start Services

```bash
docker-compose up -d  # Background mode
docker-compose up     # Foreground mode
```

### Stop Services

```bash
docker-compose down
docker-compose down -v  # Also remove volumes
```

### View Logs

```bash
docker-compose logs -f
```

## Dockerfile Variants

### Standard Dockerfile

The default `Dockerfile` creates a production-ready image with:
- Chromium browser for Playwright
- All Python dependencies
- Optimized for size

### Development Dockerfile

`Dockerfile.dev` creates a development image with:
- Hot reload support
- Development tools
- Source code mounted in container

```bash
docker build -f Dockerfile.dev -t ultraswarm:dev .
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google Gemini API key | Required |
| `BROWSER_HEADLESS` | Run browser without UI | `true` |
| `BROWSER_USE_AUTO_START` | Auto-start Chrome | `true` |
| `PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS` | Skip system validation | `1` (Arch Linux) |
| `PLAYWRIGHT_BROWSERS_PATH` | Playwright browser location | `/ms-playwright` |
| `GEMINI_MODEL` | Gemini model to use | `gemini-2.5-flash` |
| `MAX_TOKENS` | Maximum tokens for LLM | `8192` |
| `AGENT_TEMPERATURE` | LLM temperature | `0.7` |

## Volume Mounts

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `./outputs` | `/app/outputs` | Agent results |
| `./knowledge` | `/app/knowledge` | RAG knowledge base |
| `./agent_workspace` | `/app/agent_workspace` | Agent state |
| `.env` | `/app/.env` | Configuration (read-only) |

## Browser Configuration

### Arch Linux Playwright Setup

Playwright requires special handling on Arch Linux due to rolling releases. The Docker image automatically configures:

```dockerfile
PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1
PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
```

This bypasses system library version checks that may fail on Arch.

### Browser Modes

**Headless Mode (Default)**
```bash
docker-compose up -e BROWSER_HEADLESS=true
```

**headed Mode (Debug)**
```bash
docker-compose up -e BROWSER_HEADLESS=false
```

## Troubleshooting

### Chrome Not Found

If Chrome isn't found inside the container:

```bash
# Set explicit Chrome path
-e BROWSER_USE_CHROME_PATH=/usr/bin/chromium

# Or disable auto-start and connect manually
-e BROWSER_USE_AUTO_START=false
-e BROWSER_USE_CDP_URL=http://host.docker.internal:9222
```

### Permission Denied Errors

```bash
# Ensure proper permissions on mounted volumes
chmod -R 755 outputs/
chmod -R 755 knowledge/
```

### Port Already in Use

```bash
# Change CDP port
-e BROWSER_USE_CDP_PORT=9223
```

### Playwright Browser Installation Failed

```bash
# Reinstall Playwright browsers
docker-compose run ultraswarm playwright install chromium
```

### Docker Desktop WSL 2 Issues

If using Docker Desktop with WSL 2 on Windows:

```bash
# In WSL, ensure Docker is accessible
export DOCKER_HOST=unix:///var/run/docker.sock

# Restart Docker Desktop if needed
```

## Building Custom Images

```bash
# Build with specific tag
docker build -t my-ultraswarm:v1.0 .

# Build for ARM64 (Raspberry Pi, M1 Mac)
docker build --platform linux/arm64 -t ultraswarm:arm64 .

# Build with custom context
docker build --build-arg TARGETPLATFORM=linux/amd64 -t ultraswarm:custom .
```

## Using with Existing Chrome

To connect to an existing Chrome instance instead of launching a new one:

```bash
# Start Chrome manually
google-chrome --remote-debugging-port=9222

# Connect UltraSwarm
docker-compose up -e BROWSER_USE_CDP_URL=localhost:9222
```

## Performance Optimization

### Memory Limits

```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      memory: 8G
```

### Volume Mounts for Speed

```yaml
volumes:
  - browser-profile:/app/.browser-profile

volumes:
  browser-profile:
    driver: local
```

## Contributing

When modifying Docker configuration:

1. Test on Windows, Linux, and Arch Linux
2. Update this README with any changes
3. Ensure the `.dockerignore` file is updated
4. Check that all environment variables are documented
