# -*- encoding: utf-8 -*-
# WARNING: This file is managed by Puppet. Changes to this file will be overwritten.
# Script Location: /usr/lib/python2.6/site-packages/cloudbackup-1.0.01-py2.6.egg/cloudbackup/__init__.py
# File Mode: 755

### Import Python standard library modules used. #####
###### == In Use == ######
import tempfile
import os
import logging
import re
import uuid
import socket
import hashlib

from getpass import getpass
from datetime import datetime
from byteformat import ByteFormatter

#### == To be Used == ####
#import tarfile
#import fnmatch      ## for unix filename matching
#import mimetypes
#import calendar
#import functools
#from contextlib import closing  # for Python2.6 compatibility
#from gzip import GzipFile

### Import Python Third Party Modules used. #####
###### == In Use == ######
import aaargh
import yaml

#### == To be Used == ####
#from beefish import decrypt, encrypt_file
#import grandfatherson


### Import App/Tool Modules used. #####
###### == In Use == ######
from cloudbackup.backends import GlacierBackend, S3Backend, SwiftBackend
from cloudbackup.conf import encrypt_generated_pass, config, events, load_config, set_tmp_dir, DEFAULT_DESTINATION, DEFAULT_LOCATION, CONFIG_FILE, PASSWORD_4_ENCRYPTION
from cloudbackup.models import Backups
from cloudbackup.plugin import setup_plugins, plugin_setup

#### == To be Used == ####
#from cloudbackup.utils import _interval_string_to_seconds
#from cloudbackup.sync import BakSyncer, bakmanager_hook, bakmanager_periodic_backups
#from cloudbackup.plugin import setup_plugins, plugin_setup

__version__ = "1.0.01"

app = aaargh.App(description="Compress & Tar, encrypt and upload files directly to Amazon S3/Glacier/Swift.")
log = logging.getLogger("cloudbackup")
tempfile.tempdir = set_tmp_dir()

class CloudbackupFilter(logging.Filter):
    def filter(self, rec):
        if rec.name.startswith("cloudbackup") or rec.name == "root":
            return True
        else:
            return rec.levelno >= logging.WARNING

STORAGE_BACKEND = dict(s3=S3Backend, glacier=GlacierBackend, swift=SwiftBackend)


def _get_store_backend(conf, destination=None, profile="default"):
    if not isinstance(conf, dict):
        conf = load_config(conf)
    conf = conf.get(profile)
    setup_plugins(conf)
    # conf is now a hash(in perl) or a dictionary(in python).
    if not destination:
        destination = conf.get("default_destination", DEFAULT_DESTINATION)
    return STORAGE_BACKEND[destination](conf, profile), destination, conf


def get_size(start_path = os.getcwd()):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size




@app.cmd(help="Backup a file or a directory, backup the current directory if no arg is provided.")
@app.cmd_arg('filename', type=str, default=os.getcwd(), nargs="?")
@app.cmd_arg('-d', '--destination', type=str, help="s3|glacier|swift", default=None)
@app.cmd_arg('-t', '--tags', type=str, help="space separated tags", default="")
@app.cmd_arg('-b', '--blocksize', type=int, help="Upload Block Size in Bytes: Defaults to 1GB", default=1073741824)
@app.cmd_arg('-a', '--prepend_to_upload_filename', type=str, help="A prefix to stored name for upload file", default="daily")
@app.cmd_arg('-p', '--profile', type=str, default="default", help="profile name (default by default)")
@app.cmd_arg('-c', '--config', type=str, default=CONFIG_FILE, help="path to config file")
def backup(filename=os.getcwd(), destination=None, blocksize=1073741824, prepend_to_upload_filename='daily', profile="default", config=CONFIG_FILE,  tags=[], key=None, **kwargs):
    """Perform backup.

    :type filename: str
    :param filename: File/directory to backup.

    :type destination: str
    :param destination: s3|glacier|swift

    :type tags: str or list
    :param tags: Tags either in a str space separated,
        either directly a list of str (if calling from Python).

    :type conf: dict
    :keyword conf: Override/set AWS configuration.

    """
    # Backup expiry date
    # Obtain this from a fore-runner script only
    backup_expiry_date = os.getenv('expiry_date', 'None')
    prepend_to_upload_filename = os.getenv('prepend_to_upload_filename', prepend_to_upload_filename)

    storage_backend, destination, conf = _get_store_backend(config, destination, profile)

    # backup file name format: YYYY-MM-DD-HH:MM:SS-<SCHEMA>  or
    # backup file name format: YYYY-MM-DD-HH:MM:SS-<backup_filename>
    backup_file_fmt = "{1}-{0}"
    encrypted_pass_file_fmt =  "{1}-{0}"

    session_id = str(uuid.uuid4())
    events.before_backup(session_id)

    log.info("Backing up " + filename)

    # Obtaining full path to backup file.
    # this will be held in the S3 Object Metadata
    # make a copy of the filename variable without referencing it.
    file_to_upload = filename[:]
    full_path_to_dataset_for_upload = os.path.realpath(file_to_upload)

    if os.access(full_path_to_dataset_for_upload,os.R_OK):
        log.info('Full path of file/folder for upload is: [' + str(full_path_to_dataset_for_upload) + ']')
    else:
        log.error('File: [' + str(filename) + '] - check that file exists or that you have read access to this file!')
    # Obtaining full path to backup file ends.

    # Lets capture the actual filename of the file to be backed up
    arcname = filename.strip('/').split('/')[-1]  # stored in the local database.
    now = datetime.utcnow()
    # date_component = now.strftime("%Y%m%d%H%M%S")
    date_component = now.strftime("%Y-%m-%d-%H:%M:%S")
    stored_filename = backup_file_fmt.format(arcname, date_component)
    # Cloudbackup compresses, tars and encrypts all files(and or) folders to be uploaded ###
    # the suffix to the final filename tells the order of the file preprocessing. ####
    stored_filename = str(stored_filename)  +  str('.tgz.aes')
    if prepend_to_upload_filename != '':
        stored_filename = str(prepend_to_upload_filename.strip(' ')) + str(stored_filename)
    # log.info('Name(as seen in AWS-S3/Openstack swift) of Uploaded file is: [' +str( stored_filename ) +  str(']'))

    # Obtain Size of data set to be uploaded:
    if os.path.isdir(full_path_to_dataset_for_upload):
        content_upload_size = get_size(full_path_to_dataset_for_upload)
    else:
        content_upload_size = os.path.getsize(full_path_to_dataset_for_upload)

    # Backup file metadata to be stored in sqlite.
    backup_date = int(now.strftime("%s"))
    backup_data = dict(filename=kwargs.get("custom_filename", arcname ),
                       backup_date=backup_date,
                       last_updated=backup_date,
                       backend=destination,
                       is_deleted=False)

    # Collate metadata of files(actual file/folder & encryped pass file)
    # to be uploaded ( & stored in local database): Starts ###
    backup_data["size"] = content_upload_size

    # Backup encrypted pass file metadata to be stored in sqlite.
    encrypted_pass_stored_filename = str( encrypted_pass_file_fmt.format(arcname, date_component) ) + str('-encrypted_pass.txt')
    if prepend_to_upload_filename != '':
        encrypted_pass_stored_filename = str(prepend_to_upload_filename.strip(' ')) + str(encrypted_pass_stored_filename)
    backup_encrypted_passwd_file_info = dict(filename= encrypted_pass_stored_filename,
                       backup_date=backup_date,
                       last_updated=backup_date,
                       backend=destination,
                       is_deleted=False)

    # All backups must be encrypted,to meet Backup policy.
    encrypted_pass = encrypt_generated_pass(PASSWORD_4_ENCRYPTION)
    password = kwargs.get("password", PASSWORD_4_ENCRYPTION )

    length_of_pass = len(encrypted_pass)   # speculated size of encrypted pass file in bytes.
    backup_encrypted_passwd_file_info["size"] = length_of_pass

    # Handling tags metadata
    if isinstance(tags, list):
        tags = " ".join(tags)

    backup_data["tags"] = tags
    backup_encrypted_passwd_file_info["tags"] = tags

    backup_data["metadata"] = dict(is_enc=True,
                                   client=socket.gethostname(), expiry_date=backup_expiry_date)
    backup_encrypted_passwd_file_info["metadata"] = dict(is_enc=False,
                                   client=socket.gethostname(), expiry_date=backup_expiry_date)

    backup_data["stored_filename"] = stored_filename
    backup_encrypted_passwd_file_info["stored_filename"] = str(encrypted_pass_stored_filename)

    access_key = storage_backend.conf.get("access_key")
    container_key = storage_backend.conf.get(storage_backend.container_key)
    backup_data["backend_hash"] = hashlib.sha512(access_key + container_key).hexdigest()
    backup_encrypted_passwd_file_info["backend_hash"] = hashlib.sha512(access_key + container_key).hexdigest()
    # Collate metadata of files(actual file/folder & encryped pass file)
    # to be uploaded ( & stored in local database): Ends ###

    log.info("Uploading backup + encrypted pass file...")
    storage_backend.upload(stored_filename, full_path_to_dataset_for_upload, blocksize, PASSWORD_4_ENCRYPTION, encrypted_pass, encrypted_pass_stored_filename, rotate_policy=prepend_to_upload_filename)

    log.debug(backup_data)

    # Insert metadata in SQLite
    backup = Backups.create(**backup_data)
    # And for the encrypted pass file:
    backup2 = Backups.create(**backup_encrypted_passwd_file_info)

    events.on_backup(session_id, backup)
    events.on_backup(session_id, backup2)

    return backup


@app.cmd(help="Show backups list.")
@app.cmd_arg('query', type=str, default="", help="search filename for query", nargs="?")
@app.cmd_arg('-d', '--destination', type=str, default="", help="glacier|s3|swift, show every destination by default")
@app.cmd_arg('-r', '--realtime', type=str, default="false", help="Initiate real time connection to AWS S3|Glacier and retreive bucket|vault inventory.")
@app.cmd_arg('-t', '--tags', type=str, default="", help="tags space separated")
@app.cmd_arg('-p', '--profile', type=str, default="default", help="profile name (all profiles are displayed by default)")
@app.cmd_arg('-c', '--config', type=str, default=CONFIG_FILE, help="path to config file")
def show(query="", destination="", tags="", profile="default", config=CONFIG_FILE , realtime='false'):
    if realtime == 'true':
        try:
            S3instance = S3Backend()
            S3instance.show_s3_contents_in_real_time()
        except Exception as e:
            log.info("Unable to Connect in realtime to AWS S3: " + str(e))
            pass



    all_db_recorded_backups, all_db_recorded_backups_with_obtained_access_key = Backups.search(query, destination, profile=profile, tags=tags, config=config)
    if all_db_recorded_backups.count() == 0:
        log.info("From Database Records - Available backups are:")
        log.info("No Backups found!")
    elif all_db_recorded_backups_with_obtained_access_key.count() == 0:
        log.info("Database Records: No backups found for specified access key.")
        log.info("Database Records - Backups effected with a different access key other than the access key specified:")
        _display_backups(all_db_recorded_backups)
    else:
        log.info("From Database Records - Available backups are:")
        _display_backups(all_db_recorded_backups)


def _display_backups(backups):
    bytefmt = ByteFormatter()
    for backup in backups:
        backup = backup._data
        backup["backup_date"] = datetime.fromtimestamp(float(backup["backup_date"])).isoformat()
        backup["size"] = bytefmt(backup["size"])
        if backup.get("tags"):
            backup["tags"] = "({0})".format(backup["tags"])

        log.info("{backup_date}\t{backend:8}\t{size:8}\t{stored_filename} {tags}".format(**backup))


@app.cmd(help="Set AWS S3/Glacier credentials.")
@app.cmd_arg('-p', '--profile', type=str, default="default", help="profile name (default by default)")
def configure(profile="default"):
    try:
        input = raw_input
    except NameError:
        pass
    try:
        new_conf = config.copy()
        new_conf[profile] = config.get(profile, {})
        new_conf[profile]["access_key"] = input("AWS Access Key: ")
        new_conf[profile]["secret_key"] = input("AWS Secret Key: ")
        new_conf[profile]["s3_bucket"] = input("S3 Bucket Name: ")
        new_conf[profile]["glacier_vault"] = input("Glacier Vault Name: ")

        while 1:
            default_destination = input("Default destination ({0}): ".format(DEFAULT_DESTINATION))
            if default_destination:
                default_destination = default_destination.lower()
                if default_destination in ("s3", "glacier", "swift"):
                    break
                else:
                    log.error("Invalid default_destination, should be s3 or glacier, swift, try again.")
            else:
                default_destination = DEFAULT_DESTINATION
                break

        new_conf[profile]["default_destination"] = default_destination
        region_name = input("Region Name ({0}): ".format(DEFAULT_LOCATION))
        if not region_name:
            region_name = DEFAULT_LOCATION
        new_conf[profile]["region_name"] = region_name

        if default_destination in ("swift"):
            new_conf[profile]["auth_version"] = input("Swift Auth Version: ")
            new_conf[profile]["auth_url"] = input("Swift Auth URL: ")

        yaml.dump(new_conf, open(CONFIG_FILE, "w"), default_flow_style=False)

        log.info("Config written in %s" % CONFIG_FILE)
        log.info("Run bakthat configure_backups_rotation if needed.")
    except KeyboardInterrupt:
        log.error("Cancelled by user")


@app.cmd(help="Restore backup in the current directory.")
@app.cmd_arg('filename', type=str)
@app.cmd_arg('-d', '--destination', type=str, help="s3|glacier|swift", default="s3")
@app.cmd_arg('-p', '--profile', type=str, default="default", help="profile name (default by default)")
@app.cmd_arg('-c', '--config', type=str, default=CONFIG_FILE, help="path to config file")
def restore(filename, destination="s3", profile="default", config=CONFIG_FILE, **kwargs):
    """Restore backup in the current working directory.

    :type filename: str
    :param filename: File/directory to backup.

    :type destination: str
    :param destination: s3|glacier|swift

    :type profile: str
    :param profile: Profile name (default by default).

    :type conf: dict
    :keyword conf: Override/set AWS configuration.

    :rtype: bool
    :return: True if successful.
    """
    storage_backend, destination, conf = _get_store_backend(config, destination, profile)

    if not filename:
        log.error("No file to restore, use -f to specify one.")
        return

    log.info("Searching database for backup file/folder name: [" + str(filename) + str(']'))
    backup = Backups.match_filename(filename, destination, profile=profile, config=config)

    if not backup:
        log.error("No file matched.")
        log.info("To see list of all backups available, run the following commands:")
        log.info("SHELL>   cloudbackup show ")
        log.info("SHELL>   cloudbackup show --realtime=true")
        return

    session_id = str(uuid.uuid4())
    events.before_restore(session_id)

    key_name = backup.stored_filename
    log.info("Restoring " + key_name)

    is_file_encrypted = backup.is_encrypted()

    # Demand for password before download & decrypting uploaded file.
    # if key_name and backup.is_encrypted():
    #    password = kwargs.get("password")
    #    if not password:
    #        password = getpass()

    try:
        input = raw_input
    except NameError:
        pass

    if is_file_encrypted:
        log.info("Ensure that you have imported the gpg private key.")
        command = str( input("Have you imported the gpg private key: Enter 'Y' to continue or 'N' to exit & import the gpg private key: ") )
        matchObj = re.match( r'(^N)', command, re.M|re.I)
        matchObj2 = re.match( r'(^Y)', command, re.M|re.I)
        if matchObj:
            log.info("Restore process aborted!!!")
            log.info("Exiting....")
            return
        elif matchObj2:
            log.info("Downloading...")
        else:
            log.info("Unable to decode your response!")
            log.info("Restore process aborted! Retry again!")
            return
    else:
        log.info('You are about to download an encrypted pass file:')

    out = storage_backend.download(key_name, is_file_encrypted = is_file_encrypted)

@app.cmd(help="Delete a backup.")
@app.cmd_arg('filename', type=str)
@app.cmd_arg('-d', '--destination', type=str, help="s3|glacier|swift", default="s3")
@app.cmd_arg('-p', '--profile', type=str, default="default", help="profile name (default by default)")
@app.cmd_arg('-c', '--config', type=str, default=CONFIG_FILE, help="path to config file")
def delete(filename, destination="s3", profile="default", config=CONFIG_FILE, **kwargs):
    """Delete a backup.

    :type filename: str
    :param filename: stored filename to delete.

    :type destination: str
    :param destination: glacier|s3|swift

    :type profile: str
    :param profile: Profile name (default by default).

    :type conf: dict
    :keyword conf: A dict with a custom configuration.

    :type conf: dict
    :keyword conf: Override/set AWS configuration.

    :rtype: bool
    :return: True if the file is deleted.

    """
    if not filename:
        log.error("No file to delete, use -f to specify one.")
        return

    backup = Backups.match_filename(filename, destination, profile=profile, config=config)

    if not backup:
        log.error("No file matched.")
        return

    key_name = backup.stored_filename

    # Ensure the main upload file/folder is deleted first before deleting its encrypted pass file.
    # This avoids having an encrypted backup without a pass file for decryption.
    if backup.is_encrypted():
        client_about_to_delete_pass_file = False
    else:
        client_about_to_delete_pass_file =True

    storage_backend, destination, conf=_get_store_backend(config, destination, profile)

    session_id = str(uuid.uuid4())
    events.before_delete(session_id)

    log.info("Deleting {0}".format(key_name))

    return_value = storage_backend.delete(key_name, client_about_to_delete_pass_file=client_about_to_delete_pass_file)
    if return_value[0] == 1:
        backup.set_deleted()
        backup = Backups.match_filename(return_value[1], destination, profile=profile, config=config)
        backup.set_deleted()
    elif return_value[0] == 0:
        pass
    else:
        backup.set_deleted()

    events.on_delete(session_id, backup)

    return backup


def main():

    if not log.handlers:
        # logging.basicConfig(level=logging.INFO, format='%(message)s')
        handler = logging.StreamHandler()
        handler.addFilter(CloudbackupFilter())
        handler.setFormatter(logging.Formatter('%(message)s'))
        log.addHandler(handler)
        log.setLevel(logging.INFO)

    app.run()


if __name__ == '__main__':
    main()
