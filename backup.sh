#!/bin/bash

BACKUP_LOCAL="file:///media/drive/forkbomb-3.0/backup/"
LOG_DIR="/var/log/duplicity/forkbomb-3.0/"
LOG_FILE="backup.log"
LOG_CLEAR_FILE="backup_clear.log"

LOG_FULL_FILE="$LOG_DIR$LOG_FILE"
LOG_CLEAR_FULL_FILE="$LOG_DIR$LOG_CLEAR_FILE"

# If it's the first of the month, do a full backup

date=`date +%d`

if [ $date == 01 ]
then
	echo "Executing full backup"
	duplicity full --no-encryption data $BACKUP_LOCAL >>$LOG_FULL_FILE
else
	echo "Executing incremental backup"
	duplicity --no-encryption data $BACKUP_LOCAL >>$LOG_FULL_FILE
fi

# Clean up some old backups
# Remove all backups older than 1Y
duplicity remove-older-than 1Y $BACKUP_LOCAL >>$LOG_CLEAR_FULL_FILE
# Remove incrementals older than 3 months
duplicity remove-all-inc-of-but-n-full 3 $BACKUP_LOCAL >>$LOG_CLEAR_FULL_FILE


# TODO: Remote backup
# TODO: MySQL backup (plus switch to mysql)
