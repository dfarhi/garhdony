#!/bin/bash

BACKUP_LOCAL="dpbx:////forkbomb-3.0"
BACKUP_DIR="/home/i-c/django/forkbomb-3.0/data"
LOG_DIR="/var/log/duplicity/forkbomb-3.0/"
LOG_FILE="backup-dropbox.log"
LOG_CLEAR_FILE="backup-dropbox_clear.log"

LOG_FULL_FILE="$LOG_DIR$LOG_FILE"
LOG_CLEAR_FULL_FILE="$LOG_DIR$LOG_CLEAR_FILE"

# If it's the first of the month, do a full backup

# date=`date +%d`
#fulldate=$(date)

#if [ $date == 01 ]
#then
	echo "$fulldate: Executing full backup"
	duplicity full --no-encryption $BACKUP_DIR $BACKUP_LOCAL >>$LOG_FULL_FILE
#else
#	echo "$fulldate: Executing incremental backup"
#	duplicity --no-encryption $BACKUP_DIR $BACKUP_LOCAL >>$LOG_FULL_FILE
#fi

# Clean up some old backups
# Remove all backups older than 1Y
duplicity remove-older-than 1Y $BACKUP_LOCAL >>$LOG_CLEAR_FULL_FILE
# Remove incrementals older than 3 months
duplicity remove-all-inc-of-but-n-full 3 $BACKUP_LOCAL >>$LOG_CLEAR_FULL_FILE


# TODO: Remote backup
# TODO: MySQL backup (plus switch to mysql)
