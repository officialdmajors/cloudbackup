# -*- encoding: utf-8 -*-
# WARNING: This file is managed by Puppet. Changes to this file will be overwritten.
# Script Location: /usr/lib/python2.6/site-packages/cloudbackup-1.0.01-py2.6.egg/cloudbackup/backends.py
# File Mode: 755
import tempfile
import sys
import subprocess
import os
import math
import logging
import shelve
import json
import socket
import httplib
import getpass
import boto
import re
import psutil


from datetime import date
from cStringIO import StringIO
from contextlib import contextmanager

from boto.s3.key import Key
from boto.glacier.exceptions import UnexpectedHTTPResponseError
from boto.exception import S3ResponseError
from boto.s3.lifecycle import Lifecycle, Expiration, Rule, Transition, Expiration
from cloudbackup.conf import config, decrypt_encrypted_pass_file,  set_tmp_dir, DEFAULT_LOCATION, CONFIG_FILE
from cloudbackup.models import Inventory, Jobs


log = logging.getLogger(__name__)
tempfile.tempdir = set_tmp_dir()

class cloudbackupBackend(object):
    """Handle Configuration for Backends.

    The profile is only useful when no conf is None.

    :type conf: dict
    :param conf: Custom configuration

    :type profile: str
    :param profile: Profile name

    """
    def __init__(self, conf={}, profile="default"):
        self.conf = conf
        if not conf:
            self.conf = config.get(profile)
            if not self.conf:
                log.error("No {0} profile defined in {1}.".format(profile, CONFIG_FILE))
            if not "access_key" in self.conf or not "secret_key" in self.conf:
                log.error("Missing (AWS and/or OpenStack) access_key/secret_key in {0} profile ({1}).".format(profile, CONFIG_FILE))



class S3Backend(cloudbackupBackend):
    """Backend to handle S3 upload/download."""
    def __init__(self, conf={}, profile="default"):
        cloudbackupBackend.__init__(self, conf, profile)

        con = boto.connect_s3(self.conf["access_key"], self.conf["secret_key"])

        region_name = self.conf["region_name"]
        # DEFAULT_LOCATION  ==>  "us-east-1"
        if region_name == DEFAULT_LOCATION:
            region_name = ""

        try:
            self.bucket = con.get_bucket(self.conf["s3_bucket"])
        except S3ResponseError, e:
            if e.code == "NoSuchBucket":
                log.info('S3 Bucket [ ' + str(self.conf["s3_bucket"]) + ' ] does not exist...')
                log.info('Creating S3 Bucket [ ' + str(self.conf["s3_bucket"]) + ' ]...')
                try:
                    self.bucket = con.create_bucket(self.conf["s3_bucket"], location=region_name)
                except:
                    log.info('An error occured whilst trying to create bucket: [' + str(self.conf["s3_bucket"])  + ']' )
                    raise Exception
            else:
                log.info('An error occured whilst trying to connect to bucket: [' + str(self.conf["s3_bucket"])  + ']' + "\n" + 'Access key: ' + str(self.conf["access_key"])  + "\n" + 'Secret key: ' + str( self.conf["secret_key"]) + "\n" + 'Region name: ' + str(self.conf["region_name"])  )
                log.info('Check that you can connect to AWS S3 by running script: [] on the command line.')
                raise e

        self.container = self.conf["s3_bucket"]
        self.container_key = "s3_bucket"

    def return_rotation_policy_dict(self):
        # day_to_seconds = 86400        # 1 day has 86400
        # month_to_seconds = 2592000    # 30 days
        # year_to_seconds = 31536000    # 365 days
        # rotation_policy_dict = { s:1, m:60, h:3600, D:86400, W:604800, M:2592000, Y:31536000 }
        # return{ "daily":7, "weekly":28, "monthly":336, "yearly":365 }
        return {"d":7, "w":28, "m":336, "y":365}

    def life_cycle_management_enforcer(self):
        bucket = self.bucket
        lifecycle = Lifecycle()
        log.info("Checking for life cycle management rules.")
        try:
            lifecycle = bucket.get_lifecycle_config()
        except:
            log.info("No life cycle management rule configured.")

        to_glacier = Transition(days=7, storage_class='GLACIER')
        ruleid_year = 'year_long_rule'    # Unique identifier for the rule
        ruleid_month = 'month_long_rule'  # Unique identifier for the rule
        ruleid_weekly = 'week_long_rule'  # Unique identifier for the rule
        ruleid_daily = 'day_long_rule'    # Unique identifier for the rule

        dict = {
            ruleid_year: {'prefix': 'year', 'expiration':Expiration(days=365), 'transition': to_glacier},
            ruleid_month: {'prefix': 'month', 'expiration':Expiration(days=336), 'transition': to_glacier},
            ruleid_weekly: {'prefix': 'weekly', 'expiration':Expiration(days=28), 'transition': to_glacier},
            ruleid_daily: {'prefix': 'daily', 'expiration':Expiration(days=7), 'transition': None},
          }

        number_life_cycle_rules = len( lifecycle[:] )

        if  len( lifecycle[:] ) == 0:
            log.info("Creating Default Life cycle management rules.")
            for x in  dict.keys():
                lifecycle.add_rule(x, prefix=dict[x]['prefix'], expiration=dict[x]['expiration'] , transition=dict[x]['transition'])
            bucket.configure_lifecycle(lifecycle)
            log.info("Successfully created default Life cycle management rules.")

        array_list = []
        for x in range(0, number_life_cycle_rules):
            array_list.append(lifecycle[x].id)

        if len(array_list) != 0:
            for x in  dict.keys():
                if x in array_list:
                    log.info("Life Cycle Rule: [" + str(x) + "] exists!")
                    pass
                else:
                    log.info("Life Cycle Rule: [" + str(x) + "] is missing!")
                    log.info("Redefining Life Cycle Rule: [" + str(x) + "]")
                    bucket.delete_lifecycle_configuration()
                    lifecycle.add_rule(x, prefix=dict[x]['prefix'], expiration=dict[x]['expiration'] , transition=dict[x]['transition']  )
                    return_true_on_success = bucket.configure_lifecycle(lifecycle)
                    lifecycle = bucket.get_lifecycle_config()

    def show_s3_contents_in_real_time(self):
        bucket_list = self.bucket.list()
        log.info('Real time S3 object contents in bucket [' + str(self.container) + ']: ')
        for file_obj in bucket_list:
            filename_keyString = str(file_obj.key)
            akey = self.bucket.get_key(file_obj.name)
            backupsize = akey.size
            storage_class = akey.storage_class
            hostame_4rm_s3_metadata = akey.get_metadata("meta_hostname")
            os_system_user_4rm_s3_metadata = akey.get_metadata("meta_os_system_user")
            log.info('Host Out: [' + str(hostame_4rm_s3_metadata) + ']: OS System User: [' + str(os_system_user_4rm_s3_metadata) +  ']: Backup Filesize: [' + str( backupsize ) + ' Bytes]: Storage Class: [' + str(storage_class) + ']  Backup File: [' + str(filename_keyString) + '].'   )

    def decompress_decrypt_downloader(self, bucket, keyname, decrypt_pass):
        # using logging module for proccess count:
        log = logging.getLogger(__name__)
        log.setLevel(logging.DEBUG)
        format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        # Log all notice information to stderr
        log_to_console = logging.StreamHandler(sys.stderr)
        log_to_console.setFormatter(format)
        log.addHandler(log_to_console)

        def cb(complete,total):
            """Download callback to log download percentage."""
            percent = int(complete * 100.0 / total)
            log.info("Download completion: {0}%".format(percent))

        k = Key(bucket)
        k.key = keyname
        try:
            os.environ['decrypt_pass']  = decrypt_pass
            log.info("Commencing Download :: ... ")
            openssl = subprocess.Popen(
                ['openssl', 'enc',  '-base64',  '-d', '-aes-256-cbc',  '-nosalt',  '-pass', 'env:decrypt_pass'],   #### new use
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
            tar = subprocess.Popen(
                ['tar', 'xzf', '-' ],
                cwd=os.getcwd(),
                close_fds=True,
                stdin=openssl.stdout,
            )
            k.get_contents_to_file(openssl.stdin, cb=cb, num_cb=10   )
        except Exception, err:
            print (err)
        except:
            print(str(keyname) + "dowload: FAILED")
            openssl.kill()
            tar.kill()
            raise

        openssl.stdin.close()
        openssl.stdout.close()
        openssl.wait()

    def cb(self, complete, total):
        """Upload/download progress percentage callback function."""
        percent = int(complete * 100.0 / total)
        log.info("Upload completion: {0}%".format(percent))

    def download(self, keyname, is_file_encrypted=True):
        # New Download Code ### : discard commented codes below
        # k = Key(self.bucket)
        # k.key = keyname

        # encrypted_out = tempfile.TemporaryFile()
        # k.get_contents_to_file(encrypted_out)
        # encrypted_out.seek(0)

        # return encrypted_out
        decrypted_pass = None
        bucket = self.bucket
        akey = bucket.get_key(keyname)
        if not akey:
            log.info("Something isn't right!!!")
            log.info('Backup file ===> [' + str( keyname  ) + str(']: no longer exist.') )
            log.info('You may want to remove this backup entry from the list of available backups - using: ' )
            log.info(str( re.sub(r"\..*", "", __name__)) + str(' delete ') + str( keyname ))
            log.info('Exiting!')
            return

        encrypted_pass_keyname = akey.get_metadata("meta_encrypted_pass_filename")

        def cb(complete, total):
            """Download callback to log download percentage."""
            percent = int(complete * 100.0 / total)
            log.info("Download completion: {0}%".format(percent))

        def restore_file_from_glacier_to_s3 (bucket, keyname):
            akey = bucket.get_key(keyname)
            storage_class = akey.storage_class
            matchObj = re.match( r'(^glacier)', storage_class, re.M|re.I)
            if matchObj:
                log.info("File [" + str(keyname) + "] now reside in the Glacier Storage Class.")
                log.info("Restoring file [" + str(keyname) + "] from glacier to s3 for 3 days.")
                try:
                    akey.restore(days=3)
                except Exception as e:
                    log.error('Unable to initiate restoration: [' + str (e) + ']')
                    log.error('Exiting...')
                    raise
                log.info('Restoration from Glacier to S3 initialized successfully!')
                log.info('Restoration takes between 3 to 5 hours.')
                log.info('Kindly return after 5 hours and re-run the cloudbackup restore command')
                """
                ### TODO: Enable Email notification after 5 hours:
                ### By creating a schedule/cron job
                try:
                    input = raw_input
                except NameError:
                    pass
                command = str( input("Enter 'Y' to be notified or 'N' to disable notification: ") )
                matchObj = re.match( r'(^Y)', command, re.M|re.I)
                if matchObj:
                    log.info('Enabling Restoration Notification.')
                else:
                    log.info('Restoration notification is disabled')
                """
                return True
            else:
                return False

        if encrypted_pass_keyname:
            is_pass_file_in_glacier = restore_file_from_glacier_to_s3(bucket, encrypted_pass_keyname)
            is_file_in_glacier = restore_file_from_glacier_to_s3(bucket, keyname)
        elif is_file_encrypted is False:
            is_pass_file_in_glacier = restore_file_from_glacier_to_s3(bucket, keyname)
            is_file_in_glacier = is_pass_file_in_glacier
        else:
            log.error("Unable to extract password filename from Object metadata!")
            log.error('Exiting!')
            raise

        if is_file_in_glacier or is_pass_file_in_glacier:
            return

        if is_file_encrypted:
            k = Key(self.bucket)
            k.key = encrypted_pass_keyname
            pass_tmpfile = str("/tmp/") + str( os.path.basename(__file__)  )  +  str( os.getpid() )
            k.get_contents_to_filename(pass_tmpfile)

            decrypted_pass = decrypt_encrypted_pass_file(pass_tmpfile)
            if os.path.isfile(pass_tmpfile):
                os.remove(pass_tmpfile)

            if decrypted_pass == '':
                log.error("Unable to extract password for decryption.")
                return
            self.decompress_decrypt_downloader(bucket, keyname, decrypted_pass)
        else:
            k = Key(self.bucket)
            k.key = keyname
            k.get_contents_to_filename(keyname, cb=cb, num_cb=10)
            log.info('File: [' + str(keyname) + str('] restored!') )

    def iter_chunks(self, file_stream, blocksize=1073741824):
        # Default upload chunksize: 1GB = 1024 * 1024 * 1024Bytes
        free_ram = psutil.virtual_memory().free
        if isinstance(blocksize,int) and blocksize > 0.8 * free_ram:
            log.info('Low Memory: Specified upload chunk size truncated.')
            blocksize = int( 0.4 * free_ram )
        while True:
            if isinstance(blocksize,int):
                block = file_stream.read(blocksize)
            else:
                blocksize=1073741824
                block = file_stream.read(blocksize)
            if not block:
                break
            yield block

    @contextmanager
    def compress_encrypt(self, full_path_to_backup_file, PASS_4_ENCRYPTION):
        os.environ['PASS_4_ENCRYPTION'] = PASS_4_ENCRYPTION
        full_path_to_backup_file = full_path_to_backup_file.rstrip('/')
        tar = subprocess.Popen(
            ['tar', 'czf', '-', os.path.basename(full_path_to_backup_file)],
            cwd=os.path.dirname(full_path_to_backup_file),
            stdout=subprocess.PIPE,
        )
        openssl = subprocess.Popen(
            ['openssl', 'enc', '-base64', '-e', '-aes-256-cbc', '-nosalt', '-pass', 'env:PASS_4_ENCRYPTION'],
            stdin=tar.stdout,
            stdout=subprocess.PIPE,
        )

        try:
            yield openssl.stdout
        except:
            openssl.kill()
            tar.kill()
            raise
        finally:
            openssl.wait()
            tar.wait()

    def upload(self, keyname, full_path_to_backup_file, blocksize, PASS_4_ENCRYPTION, encrypted_pass, encrypted_pass_stored_filename, **kwargs):
        self.life_cycle_management_enforcer()
        backup_expiry_date = os.getenv('expiry_date', 'None')
        hostname = socket.gethostname()
        os_system_user = getpass.getuser()

        # S3 boto connect credentials ####
        k = Key(self.bucket)
        k.key = keyname

        # Setting the call back function for the upload of the encrypted password file: ###
        if kwargs.get("cb", True):
            upload_kwargs = dict(cb=self.cb, num_cb=10)

        # Extract rotation policy ####
        rotate_policy = kwargs.get('rotate_policy', 'd')
        extract_rotate_policy = rotate_policy[ 0:1 ].lower()
        rotation_policy_dict = self.return_rotation_policy_dict()
        s3_lifecycle = rotation_policy_dict.get(extract_rotate_policy, 7)

        # Set S3 Metadata here #
        # Metadata for pass file:
        k.set_metadata('meta_hostname', hostname)
        k.set_metadata('meta_os_system_user', os_system_user)
        k.set_metadata('meta_full_path_to_backup_file', full_path_to_backup_file)
        k.set_metadata('meta_backup_expiry_date', backup_expiry_date)
        k.set_metadata('meta_file_encrypted_by_this_pass_file', keyname)
        # k.set_metadata('meta_backup_encrypted_pass', encrypted_pass)
        # the encrypted_pass string is too large for s3 metadata
        # k.set_metadata('meta3', 'This is the third metadata value')
        # Metadata for actual backup file:
        keyname_metadata_dict = {
                                 'meta_hostname':hostname,
                                 'meta_os_system_user': os_system_user,
                                 'meta_full_path_to_backup_file': full_path_to_backup_file,
                                 'meta_backup_expiry_date': backup_expiry_date,
                                 'meta_encrypted_pass_filename': encrypted_pass_stored_filename
                                 }

        ##################################

        # Create temporary file to hold encrypted pass ####
        temp_File = str("/tmp/") + str( os.path.basename(__file__)  )  +  str( os.getpid() )
        with open(temp_File, 'w') as fh_obj:
            fh_obj.write(encrypted_pass)
        fh_obj.close()
        ###################################

        # The actual upload to S3 Commences below ######
        with self.compress_encrypt(full_path_to_backup_file, PASS_4_ENCRYPTION) as file_stream:
            log.info("Begin multipart upload: %r", full_path_to_backup_file)
            mp = self.bucket.initiate_multipart_upload(keyname, metadata = keyname_metadata_dict)
            try:
                for number, chunk in enumerate( self.iter_chunks(file_stream, blocksize=blocksize), 1):
                    log.info("uploading chunk %d (%d)", number, len(chunk))
                    mp.upload_part_from_file(StringIO(chunk), number)
            except:
                log.info("Aborting upload...")
                mp.cancel_upload()
                raise
            else:
                log.info("success!")
                mp.complete_upload()
        ###################################################

        # We set access control list(ACL - permissions) to private access only #####
        k.set_acl("private")

        # Uploading the encrypted pass #################
        if os.path.isfile(temp_File) and os.stat(temp_File).st_size != 0:
            k.key = str(encrypted_pass_stored_filename)
        # The actual upload of encrypted pass to S3 Commences below ######
            k.set_contents_from_filename(temp_File, **upload_kwargs)
        # We set access control list(ACL - permissions) to private access only #####
            k.set_acl("private")
            os.remove(temp_File)
        if os.path.isfile(temp_File):
            os.remove(temp_File)

    def delete(self, keyname, client_about_to_delete_pass_file=False):
        akey = self.bucket.get_key(keyname)
        if client_about_to_delete_pass_file:
            try:
               input = raw_input
            except NameError:
                pass
            log.info('You are about to delete a pass file.')
            log.info('This action will delete all backups - encrypted by this pass file.')
            command = str( input("Enter 'Y' to Continue or 'N' to Abort!!!: ") )
            matchobj = re.match( r'(^N)', command, re.M|re.I)
            matchobj2 = re.match( r'(^Y)', command, re.M|re.I)
            if matchobj:
                log.info("Delete action aborted!!!")
                log.info("Exiting....")
                return [0]
            elif matchobj2:
                log.info("Proceeding to delete pass file and all backups encrypted by the pass file ...")
                if not akey:
                    log.info("Something isn't right!!!")
                    log.info('Pass file ===> [' + str( keyname  ) + str(']: no longer exist.'))
                    file_encrypted_by_this_pass_file =  re.sub(r"(-encrypted_pass\.txt)", '.tgz.aes',  keyname)
                    log.info(str('Also deleting main file: [')  + str(file_encrypted_by_this_pass_file)  + str('].') )
                else:
                    file_encrypted_by_this_pass_file = str( akey.get_metadata("meta_file_encrypted_by_this_pass_file") )

                k1 = Key(self.bucket)
                k1.key = keyname
                k2 = Key(self.bucket)
                k2.key = file_encrypted_by_this_pass_file
                self.bucket.delete_keys([k1, k2])
                return [1, str(file_encrypted_by_this_pass_file)]
            else:
                log.info("Unable to decode your response!")
                log.info("Delete action aborted! Retry!")
                return [0]
        else:
            if not akey:
                log.info("Something isn't right!!!")
                log.info('Backup file ===> [' + str( keyname  ) + str(']: no longer exist.'))
                log.info('Proceeding to delete this entry in the local database.')
                pass_file = re.sub(r"(\.tgz\.aes)$", "-encrypted_pass.txt", keyname)
                log.info(str('Also deleting pass file [')  + str(pass_file)  + str('].'))
            else:
                pass_file = str( akey.get_metadata("meta_encrypted_pass_filename") )

            k1 = Key(self.bucket)
            k1.key = keyname
            k2 = Key(self.bucket)
            k2.key = pass_file
            self.bucket.delete_keys([k1, k2])
            return 1, str(pass_file)



class GlacierBackend(cloudbackupBackend):
    """Backend to handle Glacier upload/download."""
    def __init__(self, conf={}, profile="default"):
        cloudbackupBackend.__init__(self, conf, profile)

        con = boto.connect_glacier(aws_access_key_id=self.conf["access_key"], aws_secret_access_key=self.conf["secret_key"], region_name=self.conf["region_name"])

        self.vault = con.create_vault(self.conf["glacier_vault"])
        self.backup_key = "cloudbackup_glacier_inventory"
        self.container = self.conf["glacier_vault"]
        self.container_key = "glacier_vault"

    def load_archives(self):
        return []

    def backup_inventory(self):
        """Backup the local inventory from shelve as a json string to S3."""
        if config.get("aws", "s3_bucket"):
            archives = self.load_archives()

            s3_bucket = S3Backend(self.conf).bucket
            k = Key(s3_bucket)
            k.key = self.backup_key

            k.set_contents_from_string(json.dumps(archives))

            k.set_acl("private")

    def load_archives_from_s3(self):
        """Fetch latest inventory backup from S3."""
        s3_bucket = S3Backend(self.conf).bucket
        try:
            k = Key(s3_bucket)
            k.key = self.backup_key

            return json.loads(k.get_contents_as_string())
        except S3ResponseError, exc:
            log.error(exc)
            return {}


    def restore_inventory(self):
        """Restore inventory from S3 to local shelve."""
        if config.get("aws", "s3_bucket"):
            loaded_archives = self.load_archives_from_s3()

            with glacier_shelve() as d:
                archives = {}
                for a in loaded_archives:
                    print a
                    archives[a["filename"]] = a["archive_id"]
                d["archives"] = archives
        else:
            raise Exception("You must set s3_bucket in order to backup/restore inventory to/from S3.")

    #def upload(self, keyname, filename, **kwargs):
    def upload(self, keyname, filename,full_path_to_backup_file, encrypted_pass, encrypted_pass_stored_filename, **kwargs):
        temp_File = str("/tmp/") + str( os.path.basename(__file__)  )  +  str( os.getpid() )
        with open(temp_File, 'w') as fh_obj:
            fh_obj.write(encrypted_pass)
        fh_obj.close()
        # By Default this will upload backups in multiparts for you in chunk size of 4194304bytes(4MB) by default.
        archive_id = self.vault.concurrent_create_archive_from_file(filename, keyname)
        archive_id2 = self.vault.concurrent_create_archive_from_file(temp_File, encrypted_pass_stored_filename)
        # Create database entries for each upload with the archive id saved.
        Inventory.create(filename=keyname, archive_id=archive_id)
        Inventory.create(filename=encrypted_pass_stored_filename, archive_id=archive_id2)
        os.remove(temp_File)
        if os.path.isfile(temp_File):
            os.remove(temp_File)


        #self.backup_inventory()

    def get_job_id(self, filename):
        """Get the job_id corresponding to the filename.

        :type filename: str
        :param filename: Stored filename.

        """
        return Jobs.get_job_id(filename)

    def delete_job(self, filename):
        """Delete the job entry for the filename.

        :type filename: str
        :param filename: Stored filename.

        """
        job = Jobs.get(Jobs.filename == filename)
        job.delete_instance()

    def download(self, keyname, job_check=False, is_file_encrypted=True):
        """Initiate a Job, check its status, and download the archive if it's completed."""
        archive_id = Inventory.get_archive_id(keyname)
        if not archive_id:
            log.error("{0} not found !")
            # check if the file exist on S3 ?
            return

        job = None

        job_id = Jobs.get_job_id(keyname)
        log.debug("Job: {0}".format(job_id))

        if job_id:
            try:
                job = self.vault.get_job(job_id)
            except UnexpectedHTTPResponseError:  # Return a 404 if the job is no more available
                self.delete_job(keyname)

        if not job:
            job = self.vault.retrieve_archive(archive_id)
            job_id = job.id
            Jobs.update_job_id(keyname, job_id)

        log.info("Job {action}: {status_code} ({creation_date}/{completion_date})".format(**job.__dict__))

        if job.completed:
            log.info("Downloading...")
            encrypted_out = tempfile.TemporaryFile()

            # Boto related, download the file in chunk
            chunk_size = 4 * 1024 * 1024
            num_chunks = int(math.ceil(job.archive_size / float(chunk_size)))
            job._download_to_fileob(encrypted_out, num_chunks, chunk_size, True, (socket.error, httplib.IncompleteRead))

            encrypted_out.seek(0)
            return encrypted_out
        else:
            log.info("Not completed yet")
            if job_check:
                return job
            return

    def retrieve_inventory(self, jobid):
        """Initiate a job to retrieve Galcier inventory or output inventory."""
        if jobid is None:
            return self.vault.retrieve_inventory(sns_topic=None, description="cloudbackup inventory job")
        else:
            return self.vault.get_job(jobid)

    def retrieve_archive(self, archive_id, jobid):
        """Initiate a job to retrieve Galcier archive or download archive."""
        if jobid is None:
            return self.vault.retrieve_archive(archive_id, sns_topic=None, description='Retrieval job')
        else:
            return self.vault.get_job(jobid)

    def ls(self):
        return [ivt.filename for ivt in Inventory.select()]

    def delete(self, keyname, client_about_to_delete_pass_file=False):
        archive_id = Inventory.get_archive_id(keyname)
        if archive_id:
            self.vault.delete_archive(archive_id)
            archive_data = Inventory.get(Inventory.filename == keyname)
            archive_data.delete_instance()
            return []

            #self.backup_inventory()

    def upgrade_from_shelve(self):
        try:
            with glacier_shelve() as d:
                archives = d["archives"]
                if "archives" in d:
                    for key, archive_id in archives.items():
                        #print {"filename": key, "archive_id": archive_id}
                        Inventory.create(**{"filename": key, "archive_id": archive_id})
                        del archives[key]
                d["archives"] = archives
        except Exception, exc:
            log.exception(exc)

class SwiftBackend(cloudbackupBackend):
    """Backend to handle OpenStack Swift upload/download."""
    def __init__(self, conf={}, profile="default"):
        cloudbackupBackend.__init__(self, conf, profile)

        from swiftclient import Connection, ClientException

        self.con = Connection(self.conf["auth_url"], self.conf["access_key"],
                              self.conf["secret_key"],
                              auth_version=self.conf["auth_version"],
                              insecure=True)

        region_name = self.conf["region_name"]
        if region_name == DEFAULT_LOCATION:
            region_name = ""

        try:
            self.con.head_container(self.conf["s3_bucket"])
        except ClientException, e:
            self.con.put_container(self.conf["s3_bucket"])

        self.container = self.conf["s3_bucket"]
        self.container_key = "s3_bucket"

    def download(self, keyname):
        headers, data = self.con.get_object(self.container, keyname,
                                            resp_chunk_size=65535)

        encrypted_out = tempfile.TemporaryFile()
        for chunk in data:
            encrypted_out.write(chunk)
        encrypted_out.seek(0)

        return encrypted_out

    def cb(self, complete, total):
        """Upload callback to log upload percentage."""
        """Swift client does not support callbak"""
        percent = int(complete * 100.0 / total)
        log.info("Upload completion: {0}%".format(percent))

    def upload(self, keyname, filename, **kwargs):
        fp = open(filename, "rb")
        self.con.put_object(self.container, keyname, fp)

    def ls(self):
        headers, objects = self.con.get_container(self.conf["s3_bucket"])
        return [key['name'] for key in objects]

    def delete(self, keyname):
        self.con.delete_object(self.container, keyname)
