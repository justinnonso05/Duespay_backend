#!/usr/bin/env bash
set -o errexit
gunicorn config.wsgi:application --env DJANGO_SETTINGS_MODULE=config.settings.prod