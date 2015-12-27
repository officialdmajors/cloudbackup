#!/usr/bin/env python
# WARNING: This file is managed by Puppet. Changes to this file will be overwritten.
# AUTHOR                 = IKECHUKWU MACDAVID UMEJIOFOR (MAJOR)
# EMAIL                  = officialdmajors@gmail.com
# DATE                   = 12 October 2015
# PHONE                  = 07867430002
# SCRIPT/FILE PURPOSE    = This script performs the actual backup(i.e. upload) to the cloud(AWS or Openstack).
# SCRIPT LOCATION = '/usr/lib/python2.6/site-packages/cloudbackup-1.0.01-py2.6.egg/cloudbackup/run_cloudbackup.py'
# Quick Shortcut to Delete All backups from commanline:
# for x in `cloudbackup show 2>&1 | awk '{print $5}'`; do echo $x; cloudbackup delete $x  -d s3;  done


import peewee
from datetime import datetime
import os
import time
import json
import sqlite3
import logging
import subprocess
import sys
import logging.handlers
import shutil
import re
import getpass


DATABASE = os.path.expanduser("~/.cloudbackup.sqlite")
### Instantiate the database file:
database = peewee.SqliteDatabase(DATABASE)
class JsonField(peewee.CharField):
    """Custom JSON field."""
    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        try:
            return json.loads(value)
        except:
            return value


class Backups(peewee.Model):
    """Backups Model."""
    backend = peewee.CharField(index=True)
    backend_hash = peewee.CharField(index=True, null=True)
    backup_date = peewee.IntegerField(index=True)
    filename = peewee.TextField(index=True)
    is_deleted = peewee.BooleanField()
    last_updated = peewee.IntegerField()
    metadata = JsonField()
    size = peewee.IntegerField()
    stored_filename = peewee.TextField(index=True, unique=True)
    tags = peewee.CharField()
    class Meta:
          database = database

# Variables declaration:
expired_backups_to_be_deleted = []
backup_home_dir              = '/usr/share/dmajors/cloudbackup/run_cloudbackup'
# backup_home_dir = '<%= @backup_home_dir %>'   # Should be supplied by puppet
cloudbackup_logs_directory = '/var/log/cloudbackup'   # Directory created by puppet
# Script tmp log file:
logfile = str( cloudbackup_logs_directory ) + str('/') + str( os.path.basename(__file__)) + str('.log.') + str( os.getpid())
tmp_logfile = str("/tmp/") + str( os.path.basename(__file__)) + str('.log.') + str( os.getpid())
# Files or directories to be backed up - enter multiple values separated by comma:
# backup_paths_info = '/root/major:1M,/var/lib/mysql:2M,/var/log/mysql'   # comma separated values(just an example)
backup_paths_info = '<%= @data_paths_to_backup  %>'   # comma separated values supplied by puppet
backup_paths_info_array = backup_paths_info.split(',')
# backup_path_array = [ 'mysql', 'kanu' ]
backup_path_array = backup_paths_info_array
files_folders_to_backup = []
# Backup Filenames uploaded to the cloud:
Year_Long_Full_backup_File = ''
Month_Long_Full_backup_File = ''
Week_Long_Full_backup_File = ''
CONFIG_FILE = os.path.expanduser("~/.cloudbackup.yml")
SQLITE_DB_FILE = os.path.expanduser("~/.cloudbackup.sqlite")
SQLITE_DB_FILE_EXISTS = 0  # 0 ==> doesn't exist, 1 ==> exists
pre_existing_backups = False
backup_filenames_array = []
DATABASE = os.path.expanduser("~/.cloudbackup.sqlite")
# Instantiate the database file:
database = peewee.SqliteDatabase(DATABASE)

# Little Doc:
# First we query the sqllite database to find out
# whether a backup for the following exists:

# Programmatic Logic(Business Logic translation)
# A). Year Long Backup
# 1). Keep the first ever successful full backup(or oldest full backup) for a year -
# In the year that follows, delete this backup, and mark the first full backup of
# the current month/day(or oldest full backup of the current month/day) as the new candidate
# for the year long backup. Ensure that the new full backup exists before deleting the old backup.
# Save this backup file-name/folder in the database(a file DB and SQL database - mariadb, dynamodb e.t.c.).
# Lets call this file: Year_Long_Full_backup_File

# B). Month Long Backup
# 1).  Keep the first ever successful full backup(or oldest full backup)
# in the current month to last for a month.
# Save this backup file-name/folder in the database(a file DB and SQL database - mariadb, dynamodb e.t.c.).
# For every run during the day, check that this backup exists and report/alert if it is missing.
# If missing promote next in line backup file in its place and retain it in the database as the new month long backup.
# Lets call this file: Month_Long_Full_backup_File

# C). Week Long Backup
# Ensure that a full backup exists for the last week. Where you have daily full
# backup lasting more than one week, elect one of the oldest surviving for the week and save this in the database.
# Lets call this file: Week_Long_Full_backup_File

# D). For Daily Full backups:
# Every backup in this category should have a shelve life of 7 days(TBD*).
# These backups can qualify for the year long backup, month long backup and week long back

# E). Transaction Backups(Binary Logs)
# Should take place hourly.
# should be implemented using aws cli - which enables/utilizes rsync
# features. boto api doesn't support this as at Nov/2015.
# These backups should have a naming convention to match their full backups counterpart for that day.
# These backups will have same shelve life(7 days) as their daily full backups.
# They should be rotated only - if and when their daily full backup counterparts are deleted.

# PayLoad:
# Enable logging to console and to log file: starts -
# -- Ensure our log directory exist or that we can create it: -- #
if not os.path.exists(cloudbackup_logs_directory):
   try:
       os.makedirs(cloudbackup_logs_directory)
   except:
       # if not lets use tmp directory:
       logfile = tmp_logfile
       pass

LOGFILE = logfile
logger = logging.getLogger("")
# Logging levels: choose any one of the levels below:
# each one covers the others below it: eg. DEBUG logs(debug, info, warnings, errors and criticals)
# logger.setLevel(logging.DEBUG)      # DEBUG logs(debug, info, warnings, errors and criticals)
logger.setLevel(logging.INFO)      # INFO logs(info, warnings, errors and criticals)
# logger.setLevel(logging.WARNING)   # WARNING logs(warnings, errors and criticals)
# logger.setLevel(logging.ERROR)     # ERROR logs(errors and criticals)
# logger.setLevel(logging.CRITICAL)  # ERROR logs(criticals)
formating = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# Rotate the logs between 2 files(LOGFILE - sample.log & sample.log1 ) size maxBytes(combined size for both files) ####
# In the code that follows, we set( files sample.log and sample.log1 to sum up to 90MB)and keep rotating afterwards.
# handler = logging.handlers.RotatingFileHandler(    LOGFILE, maxBytes=(90000000), backupCount=1 )
# You can use the maxBytes and backupCount values to allow the file to rollover at a predetermined size.
# When the size is about to be exceeded, the file is closed and a new file is silently opened for output.
# Rollover occurs whenever the current log file is nearly maxBytes in length; if either of maxBytes
# or backupCount is zero, rollover never occurs. If backupCount is non-zero, the system will
# save old log files by appending the extensions '.1','.2' etc., to the filename.
# For example, with a backupCount of 5 and a base file name of app.log, you would get app.log,
# app.log.1, app.log.2, up to app.log.5. The file being written to is always app.log.
# When this file is filled, it is closed and renamed to app.log.1, and if files app.log.1, app.log.2,
# etc. exist, then they are renamed to app.log.2, app.log.3 etc. respectively.
#  Do not rotate logs: #####
try:
    handler = logging.handlers.RotatingFileHandler(LOGFILE, maxBytes=(0), backupCount=0 )
except:
    LOGFILE = tmp_logfile
    logfile = LOGFILE
    handler = logging.handlers.RotatingFileHandler(LOGFILE, maxBytes=(0), backupCount=0 )
    pass

handler.setFormatter(formating)
logger.addHandler(handler)
# For console logging we want it to go to standard err.
log_to_console = logging.StreamHandler(sys.stderr)       # print loggings to standard err
# log_to_console = logging.StreamHandler(sys.stdout)     # print loggings to standard out
log_to_console.setFormatter(formating)
logger.addHandler(log_to_console)
# Testing the logger goes both to screen and log file:
# logger.debug("This is a debug message")
# logger.info("Informational message")
# logger.error("An error has happened!")
# Enable logging to console and to log file: ends.

# Check if a local copy of the cloudbackup metadata file exists: SQLITE_DB_FILE_EXISTS
if os.path.exists(SQLITE_DB_FILE) and os.access(SQLITE_DB_FILE,os.R_OK):
    SQLITE_DB_FILE_EXISTS +=1   # if the private import is successful, this should always return true.
    logger.info('OUT: Local DB File: [' + str(SQLITE_DB_FILE) + '] is accessible.')

# Function Definitions:

def return_os_system_user():
    return getpass.getuser()

def return_rotation_policy_dict():
    # day_to_seconds = 86400        # 1 day has 86400 seconds
    # month_to_seconds = 2592000    # 30 days
    # year_to_seconds = 31536000    # 365 days
    # rotation_policy_dict = { s:1, m:60, h:3600, D:86400, W:604800, M:2592000, Y:31536000 }
    return {"d": 7, "w": 28, "m": 336, "y": 365}

def check_for_backups_with_known_policies(filename, policy='year'):
    filename = filename.strip('/').split('/')[-1]
    # Check table exists and effect query.
    if Backups.table_exists():
        # query to run: select * from Backups where is_deleted = 0 and stored_filename like 'year%' and filename like 'filename*'
        # query for
        policy = "{0}*".format(policy)
        like_me = "{0}*".format(filename)
        query =  Backups.select().where(Backups.is_deleted == 0, peewee.fn.Lower(Backups.stored_filename) % policy, peewee.fn.Lower(Backups.filename) % like_me)
        #query = Backups.select().where(Backups.is_deleted == 0, peewee.fn.Lower(Backups.stored_filename) % 'year*', peewee.fn.Lower(Backups.filename) % like_me)
        query = query.order_by(Backups.backup_date.asc())
        #backup_filenames = query.get()
        rows = query
        row_count = query.count()
        if row_count >= 1:
            backup_that_meets_policy_exists = False
            for x in rows:
                # print('Filename prior to upload: [' + str(x.filename)  + '] ' + 'Filename on upload: [' + str(x.stored_filename) + ']')
                # print('Backup date for file: [' + str(x.stored_filename) + ']: ', x.backup_date )
                backup_file_date = x.backup_date
                backup_rentention_period = str(x.stored_filename[0:1]).lower()
                # print('backup string: [' + str(backup_rentention_period) + str('].'))
                anticipated_backup_expiry_date_in_seconds = return_rotation_policy_dict().get(backup_rentention_period, 7) * 86400 + backup_file_date
                # print('anticipated_backup_expiry_date: ', time.strftime('%Y-%m-%d %H:%M:%S', time.localtime( anticipated_backup_expiry_date_in_seconds)) )
                # print('Existing Tags: [' + str(x.tags) + str(']'))
                # tag = x.tags
                epoch_to_python_date = datetime.fromtimestamp(backup_file_date)
                year_backup_created = epoch_to_python_date.strftime("%Y")
                month_in_year_backup_created = epoch_to_python_date.strftime("%B")
                week_in_year_backup_created = epoch_to_python_date.strftime("%U")
                day_in_week_backup_created = epoch_to_python_date.strftime("%A")
                # print('Backup_year: [' + str(year_backup_created)  + str(']'))
                # print('Backup_month_in_year: [' + str(month_in_year_backup_created)  + str(']'))
                #print('Backup_week_in_year: [' + str(week_in_year_backup_created)  + str(']'))
                # print('Backup_Day_in_week: [' + str(day_in_week_backup_created)  + str(']'))
                backup_tag = str.join(':', (year_backup_created, month_in_year_backup_created, week_in_year_backup_created, day_in_week_backup_created))
                backup_tag_tuple = (year_backup_created, month_in_year_backup_created, week_in_year_backup_created, day_in_week_backup_created)
                # print('Backup tag: [' + str(backup_tag) + str('].'))
                now = datetime.utcnow()
                current_date_in_seconds = int(now.strftime("%s"))
                current_year = now.strftime("%Y")
                current_month_in_year = now.strftime("%B")
                current_week_in_year = now.strftime("%U")
                current_Day_in_week = now.strftime("%A")
                # print('current_year: [' + str(current_year)  + str(']'))
                # print('current_month_in_year: [' + str(current_month_in_year)  + str(']'))
                # print('current_week_in_year: [' + str(current_week_in_year)  + str(']'))
                # print('current_Day_in_week: [' + str(current_Day_in_week)  + str(']'))
                current_tag = str.join(':', (current_year, current_month_in_year, current_week_in_year, current_Day_in_week))
                current_tag_tuple =  (current_year, current_month_in_year, current_week_in_year, current_Day_in_week)
                # print('Current tag: [' + str(current_tag) + str('].'))
                if current_date_in_seconds > anticipated_backup_expiry_date_in_seconds:
                    logger.info('File: [' + str(x.stored_filename) + '] will be deleted!' )
                    expired_backups_to_be_deleted.append(x.stored_filename)
                elif backup_rentention_period == 'd' and backup_tag_tuple == current_tag_tuple:
                    backup_that_meets_policy_exists = True
                    logger.info('File: [' + str(x.stored_filename) + '] will be retained!' )
                elif backup_rentention_period == 'w' and backup_tag_tuple[0:3] == current_tag_tuple[0:3]:
                    backup_that_meets_policy_exists = True
                elif backup_rentention_period == 'm' and backup_tag_tuple[0:2] == current_tag_tuple[0:2]:
                    backup_that_meets_policy_exists = True
                elif backup_rentention_period == 'y' and backup_tag_tuple[0:1] == current_tag_tuple[0:1]:
                    backup_that_meets_policy_exists = True
            if backup_that_meets_policy_exists:
                return True
            else:
                return False
        else:
            return False


def check_todays_backup_inventory_for_file(filename):
    filename = filename.strip('/').split('/')[-1]
    now = datetime.utcnow()
    current_date_in_seconds = int(now.strftime("%s"))
    current_year = now.strftime("%Y")
    current_month_in_year = now.strftime("%B")
    current_week_in_year = now.strftime("%U")
    current_Day_in_week = now.strftime("%A")
    current_Hour_in_day = now.strftime("%H")
    current_Hour_in_day = 1 if current_Hour_in_day == '00' else current_Hour_in_day
    current_Hour_in_day= int( str(current_Hour_in_day).lstrip("0")  )
    seconds_elapsed_since_00hr = current_Hour_in_day * 3600
    date_in_seconds_at_00hr = current_date_in_seconds - seconds_elapsed_since_00hr

    current_tag = str.join(':', (current_year, current_month_in_year, current_week_in_year, current_Day_in_week))
    if Backups.table_exists():
        like_me = "{0}*".format(filename)
        query =  Backups.select().where(Backups.is_deleted == 0, Backups.backup_date >= date_in_seconds_at_00hr, peewee.fn.Lower(Backups.filename) % like_me)
        query = query.order_by(Backups.backup_date.desc())
        #backup_filenames = query.get()
        rows = query
        row_count = query.count()
        if row_count >= 1:
            return  True
        else:
            logger.info('No Backups found for file: [' + str(filename) + str('] since ') + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(date_in_seconds_at_00hr)))
            return False
    else:
        return False

def run_backup(cmd, filename):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=1)
    for line in iter(p.stdout.readline, b''):
        logger.info( str(line) )
    p.stdout.close()
    p_status = p.wait()
    if int(p_status) == 0:
        logger.info('OUT: Backup of path: [' + str(filename) + '] was successful!' )
    else:
        logger.error('OUT: Backup of path: [' + str(filename) + '] was unsuccessful!' )

def run_delete(cmd, filename):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=1)
    for line in iter(p.stdout.readline, b''):
        logger.info( str(line) )
    p.stdout.close()
    p_status = p.wait()
    if int(p_status) == 0:
        logger.info('OUT: Purge of Backup file: [' + str(filename) + '] was successful!' )
    else:
        logger.error('OUT: Purge of Backup file: [' + str(filename) + '] was unsuccessful!' )

def year_long_backup(backup_path_array):
    dict_paths_to_backup = {}
    # run_backup = False
    for filename in backup_path_array:
        logger.info("Checking backup inventory for year long backup of file: [" + str(filename) + str('].') )
        if not check_todays_backup_inventory_for_file(filename):
            # run_backup = True
            if filename in dict_paths_to_backup:
                dict_paths_to_backup += 1
            else:
                dict_paths_to_backup[filename] = 1
        year_long_backup_exists = check_for_backups_with_known_policies(filename, policy='year')
        if not year_long_backup_exists  and filename in dict_paths_to_backup:
            logger.info('Trigger backup for file: ' + str(filename) + str('].'))
            if os.path.exists(filename) and os.access(filename, os.W_OK):
                cmd = ['cloudbackup', 'backup' , filename , '-a', 'year' ]
                run_backup(cmd, filename)
            else:
                logger.error('ERROR: Path: [' + str(filename) + '] - does not exist or is unreadable by user: [' + str(return_os_system_user()) + '].' )
        else:
            logger.info('No action to undetake for file: ' + str(filename) + str('].'))
            # Check.


def month_long_backup(backup_path_array):
    """This function checks for an existing month long backup using the backup metadata on the host.
    If a month long backup exists, confirm its not over 30 days old.
    if its over 30 days old, effect a new s3 backup and mark the backup as a month long backup.
    Confirm that the backup completed successfully before purging(deleting) the month long backup that has stayed more than 30 days old

    If none(no month long backup) exists, effect an s3 backup and have it tagged(or marked) as the month long backup.
    """

    # run_backup = False
    dict_paths_to_backup = {}
    for filename in backup_path_array:
        logger.info("Checking backup inventory for month long backup of file: [" + str(filename) + str('].') )
        if not check_todays_backup_inventory_for_file(filename):
            # run_backup = True
            if filename in dict_paths_to_backup:
                dict_paths_to_backup += 1
            else:
                dict_paths_to_backup[filename] = 1
        month_long_backup_exists = check_for_backups_with_known_policies(filename, policy='month')
        if not month_long_backup_exists  and filename in dict_paths_to_backup:
            logger.info('Trigger backup for file: ' + str(filename) + str('].'))
            if os.path.exists(filename) and os.access(filename, os.W_OK):
                cmd = ['cloudbackup', 'backup' , filename , '-a', 'month' ]
                run_backup(cmd, filename)
            else:
                logger.error('ERROR: Path: [' + str(filename) + '] - does not exist or is unreadable by user: [' + str(return_os_system_user()) + '].' )
        else:
            logger.info('No action to undetake for file: ' + str(filename) + str('].'))
            # Check.


def week_long_backup(backup_path_array):
    """This function checks for an existing month long backup using the backup metadata on the host.
    If a month long backup exists, confirm its not over 30 days old.
    if its over 30 days old, effect a new s3 backup and mark the backup as a month long backup.
    Confirm that the backup completed successfully before purging(deleting) the month long backup that has stayed more than 30 days old

    If none(no month long backup) exists, effect an s3 backup and have it tagged(or marked) as the month long backup.
    """
    # run_backup = False
    dict_paths_to_backup = {}
    for filename in backup_path_array:
        logger.info("Checking backup inventory for week long backup of file: [" + str(filename) + str('].') )
        if not check_todays_backup_inventory_for_file(filename):
            # run_backup = True
            if filename in dict_paths_to_backup:
                dict_paths_to_backup += 1
            else:
                dict_paths_to_backup[filename] = 1
        week_long_backup_exists = check_for_backups_with_known_policies(filename, policy='week')
        if not week_long_backup_exists  and filename in dict_paths_to_backup:
            logger.info('Trigger backup for file: ' + str(filename) + str('].'))
            if os.path.exists(filename) and os.access(filename, os.W_OK):
                cmd = ['cloudbackup', 'backup' , filename , '-a', 'weekly' ]
                run_backup(cmd, filename)
            else:
                logger.error('ERROR: Path: [' + str(filename) + '] - does not exist or is unreadable by user: [' + str(return_os_system_user()) + '].' )
        else:
            logger.info('No action to undetake for file: ' + str(filename) + str('].'))
            # Check.

def day_long_backup(backup_path_array):
    dict_paths_to_backup = {}
    # run_backup = False
    for filename in backup_path_array:
        logger.info("Checking backup inventory for day long backup of file: [" + str(filename) + str('].') )
        if not check_todays_backup_inventory_for_file(filename):
            # run_backup = True
            if filename in dict_paths_to_backup:
                dict_paths_to_backup += 1
            else:
                dict_paths_to_backup[filename] = 1
        day_long_backup_exists = check_for_backups_with_known_policies(filename, policy='daily')
        if not day_long_backup_exists  and filename in dict_paths_to_backup:
            logger.info('Trigger backup for file: ' + str(filename) + str('].'))
            if os.path.exists(filename) and os.access(filename, os.W_OK):
                cmd = ['cloudbackup', 'backup' , filename , '-a', 'daily' ]
                run_backup(cmd, filename)
            else:
                logger.error('ERROR: Path: [' + str(filename) + '] - does not exist or is unreadable by user: [' + str(return_os_system_user()) + '].' )
        else:
            logger.info('No action to undetake for file: ' + str(filename) + str('].'))


year_long_backup(backup_path_array)
month_long_backup(backup_path_array)
week_long_backup(backup_path_array)
day_long_backup(backup_path_array)

logger.info('expired_backups_to_be_deleted: ' + str( expired_backups_to_be_deleted))

if len(expired_backups_to_be_deleted) >= 1:
    for stored_filename in expired_backups_to_be_deleted:
        cmd = ['cloudbackup', 'delete' , stored_filename ]
        run_delete(cmd, stored_filename)
    # Prunning of local sqlite db for deleted objects:
    # QUERY: delete from backups where is_deleted = 1;
    logger.setLevel(logging.DEBUG)
    query = Backups.delete().where(Backups.is_deleted == 1)
    number_of_rows_deleted = query.execute()
    logger.info(str(number_of_rows_deleted) + str('rows deleted from local DB instance.'))



new_logfile = re.sub('\.\d+$', '',logfile )

with open(new_logfile, 'a') as outfile:
        with open(LOGFILE) as infile:
            outfile.write(infile.read())
        outfile.write('########################' * 4)

if os.path.isfile(logfile):
    os.remove(logfile)