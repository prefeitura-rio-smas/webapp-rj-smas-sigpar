#!/bin/sh
set -eu
set -a
. /etc/sigpar/sigpar-prod.env
set +a
exec sudo -u sigpar-prod env \
  SIGPAR_DB="$SIGPAR_DB" \
  SIGPAR_BACKUP_SHEET_ID="$SIGPAR_BACKUP_SHEET_ID" \
  SIGPAR_BACKUP_SA_KEY="$SIGPAR_BACKUP_SA_KEY" \
  /opt/sigpar/prod/current/.venv/bin/python \
  /opt/sigpar/prod/current/jobs/backup_to_sheet.py
