#!/usr/bin/env bash
set -o errexit
source venv/Scripts/activate
python manage.py runserver
