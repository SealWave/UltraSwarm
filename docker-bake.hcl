// Docker Buildx bake file for multi-platform builds
// Usage: docker buildx bake -f docker-bake.hcl

variable "REGISTRY" {
  default = "docker.io"
}

variable "IMAGE_NAME" {
  default = "ultraswarm"
}

variable "VERSION" {
  default = "latest"
}

group "default" {
  targets = ["ultraswarm"]
}

target "ultraswarm" {
  context    = "."
  dockerfile = "Dockerfile"
  
  platforms = [
    "linux/amd64",
    "linux/arm64"
  ]
  
  tags = [
    "${REGISTRY}/${IMAGE_NAME}:${VERSION}",
    "${REGISTRY}/${IMAGE_NAME}:latest"
  ]
  
  args = {
    TARGETPLATFORM = "${platform}"
    BUILDPLATFORM  = "linux/amd64"
  }
  
  labels = {
    "org.opencontainers.image.title"       = "UltraSwarm"
    "org.opencontainers.image.description" = "Multi-agent AI swarm for e-commerce automation"
    "org.opencontainers.image.version"     = "${VERSION}"
    "org.opencontainers.image.source"      = "https://github.com/your-repo/ultraswarm"
  }
  
  cache-from = ["type=registry,ref=${REGISTRY}/${IMAGE_NAME}:cache"]
  cache-to   = ["type=registry,ref=${REGISTRY}/${IMAGE_NAME}:cache,mode=max"]
}

target "ultraswarm-dev" {
  context    = "."
  dockerfile = "Dockerfile.dev"
  
  tags = ["${REGISTRY}/${IMAGE_NAME}:dev"]
  
  args = {
    TARGETPLATFORM = "linux/amd64"
    BUILDPLATFORM  = "linux/amd64"
  }
}
