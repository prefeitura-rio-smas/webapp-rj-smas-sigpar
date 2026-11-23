#!/bin/sh
set -eu
set -a
. /etc/sigpar.env
set +a
exec /usr/bin/python3 /root/sigpar/jobs/backup_to_sheet.py
