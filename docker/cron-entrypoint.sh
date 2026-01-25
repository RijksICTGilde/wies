#!/usr/bin/env bash
set -e

# Install crontab
crontab /app/docker/crontab

echo "Starting cron scheduler..."
echo "Scheduled tasks:"
crontab -l

# Run cron in foreground
exec cron -f
