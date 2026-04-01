#!/usr/bin/env bash
set -euo pipefail

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required but not installed."
  exit 1
fi

echo "Installing Docker CLI, Compose plugin, and Colima..."
brew install docker docker-compose colima

mkdir -p "${HOME}/.docker/cli-plugins"
ln -sf /opt/homebrew/opt/docker-compose/bin/docker-compose "${HOME}/.docker/cli-plugins/docker-compose"

if ! colima status 2>/dev/null | grep -qi "running"; then
  echo "Starting Colima VM (Docker runtime)..."
  colima start
fi

docker version
docker compose version
echo "Docker is ready. Use: docker ps"
