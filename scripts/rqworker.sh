#!/bin/sh
set -e
exec python manage.py rqworker punch default --verbosity 1
