cloudbackup
-----------
cloudbackup provides a command line interface for backups management in the cloud(Amazon S3, Amazon Glacier and Openstack swift ) on client hosts.

It is based on Bakthat Release v0.6.0 - which is an MIT licensed backup framework written in Python. 

For more information on Bakthat - see: [Bakthat User Guide.](https://media.readthedocs.org/pdf/bakthat/latest/bakthat.pdf)

cloudbackup - a puppet module, although based on bakthat, is a complete re-write and provide a means to backup files/folders to the cloud(Amazon S3, Amazon Glacier and Openstack swift ).

Using cloudbackup as a puppet module.
----------------------------------------

1.   Minimum Hieradata Required to Push to both s3 and glacier : 

           ################### S3 Details #########################
           region_name:                       xxxxxxxxxxxxxxxx
           s3_bucket_name:                    xxxxxxxxxxxxxxxx
           access_key:                        xxxxxxxxxxxxxxxx
           secret_key:                        xxxxxxxxxxxxxxxx
           ################ Backup information ####################
           data_paths_to_backup:                 '/path/to/backup1,/path/to/backup2,/path/to/backup3'      ( Specify the different paths(files or folders) to be uploaded/backedup - each separated by comma. )

Upload notes:

data_paths_to_backup:

Here you list out the paths to the various files/folders you want to upload(or backup) - each separated by comma.

2.   Including cloudbackup in your Service puppet Module

Your service module will need a dependancy added to it's Modulefile.

    dependency 'cloudbackup', 'x.x.x'

We suggest leaving the bug fix number as 'x', to ensure your deployment receives any updates and fixes.

To install Cloudbackup simply call the class OR include it from any manifest in your service module.

    include cloudbackup

or

    class { 'cloudbackup': }

For the particular node, you intend to have the cloud backup installed, you can introduce a hiera data in 
your service module -  and have an if statement check for the value:

       $activate_cloud_backup                    = hiera('activate_cloud_backup', 'false')

       if ( $activate_cloud_backup == 'true' ){
       class { 'cloudbackup': }
       }

Or

       if ( $activate_cloud_backup == 'true' ){
       include cloudbackup
       }


3.   Generate content for other aspects of your module


4.   Prepare your module by running a script in the root of the service module directory


5.   Commit and push to git


A quick command reference for: cloudbackup
------------------------------------------------------------------------
The cli command on a linux host is cloudbackup.

Without making modifications to this puppet module, you can simply use the command line examples below in your custom backup scripts.

--- To see the help guide for the backup subcommand - on the command line prompt type in:

     Shell-Prompt> cloudbackup backup --help

     ######## Sample Output ########

     usage: cloudbackup backup [-h] [-d DESTINATION] [-t TAGS] [-b BLOCKSIZE]
                               [-a PREPEND_TO_UPLOAD_FILENAME] [-p PROFILE]
                               [-c CONFIG]
                               [filename]

     positional arguments:
     filename

     optional arguments:
       -h, --help            show this help message and exit
       -d DESTINATION, --destination DESTINATION
                        s3|glacier|swift
       -t TAGS, --tags TAGS  space separated tags
       -b BLOCKSIZE, --blocksize BLOCKSIZE
                        Upload Block Size in Bytes: Defaults to 1GB
       -a PREPEND_TO_UPLOAD_FILENAME, --prepend_to_upload_filename PREPEND_TO_UPLOAD_FILENAME
                        A prefix to stored name for upload file
       -p PROFILE, --profile PROFILE
                        profile name (default by default)
       -c CONFIG, --config CONFIG
                        path to config file
     
     ##################################

--- To see all subcommands offered:

Shell-Prompt> cloudbackup -h

     ########## Sample Output #########
     $ cloudbackup -h
     usage: cloudbackup [-h] {restore,delete,backup,configure,show} ...     <===  subcommands

     Compress & Tar, encrypt and upload files directly to Amazon S3/Glacier/Swift.

     optional arguments:
       -h, --help            show this help message and exit

     Subcommands:
       {restore,delete,backup,configure,show}
         backup              Backup a file or a directory, backup the current
                             directory if no arg is provided.
         show                Show backups list.
         configure           Set AWS S3/Glacier credentials.
         restore             Restore backup in the current directory.
         delete              Delete a backup.
     $
     ##################################
     

Command Examples for script customization (Run the following commands as the backup user. By default this is the root user):
--------------------------------------------------------------------------------------------------

a). To Backup Folder/File:   kalasis/ 

        cloudbackup   backup    kalasis 

b). To list out files uploaded to both s3 and glacier by cloudbackup command(Note this reads the local sqlite database - ~/.cloudbackup.sqlite ):

        cloudbackup show

c). To list out files uploaded to both s3 and glacier in real time:
 
         cloudbackup show -r true
 
d). To delete files uploaded to s3

         cloudbackup delete  <s3-uploaded-backup-with-timestamp>

or

         cloudbackup delete  daily2015-11-17-04:45:45-mysql.tgz.aes

e). To restore backed up file name: kalasis (from s3 to working directory)

         cloudbackup restore kalasis                (==> this restores the latest )

f). To restore specific timestamped backed up file name: daily2015-11-17-04:45:45-mysql.tgz.aes (mysql from s3) to working directory

         cloudbackup restore daily2015-11-17-04:45:45-mysql.tgz.aes
         

     #### Note ####

     Where an s3 object(upload) has been transitioned into a glacier storage,
     the restore subcommand simply triggers a restore to S3 from glacier. You 
     will be notified to allow for 3-5hours for the upload to arrive in S3 from 
     glacier. After this time interval(and eventual transition from glacier to S3 ), 
     simply re-run the restore subcommand to download/restore your backup.

     ##############



License
-------
Copyright 2015 OfficialDmajor's.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Contact
-------
Email: <officialdmajors@gmail.com>


Web: <dmajors.com>

Groups: <officialdmajors@gmail.com>

Support
-------

Please log tickets and issues at our [Projects Site](https://dmajors.com)
