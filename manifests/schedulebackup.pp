class cloudbackup::schedulebackup (
  $data_paths_to_backup, $backup_home_dir, $backup_user, $backup_group,

){

#### Deploy actual cloud backup script ####
    file { 'cloudbackup_script':
        path      => "/usr/lib/python2.6/site-packages/cloudbackup-1.0.01-py2.6.egg/cloudbackup/run_cloudbackup.py",
        owner     => "$backup_user",
        group     => "$backup_group",
        #replace   => "false",
        mode      => '755',
        content   => template('cloudbackup/backupscripts/run_cloudbackup.py')
    }

#### Deploy actual cloud backup cron job ####
    file { 'cloudbackup_cronjob':
        path      => "/etc/cron.d/cloudbackup_jobs",
        owner     => "$backup_user",
        group     => "$backup_group",
        #replace   => "false",
        mode      => '644',
        content   => template('cloudbackup/cronjobs/cloudbackup_jobs')
    }


##### Script to execute/run to ascertain connectivity to AWS S3 ####
    file { 'cloudbackup_test_s3_connection':
        path      => "$backup_home_dir/test_s3_connection.py",
        owner     => "$backup_user",
        group     => "$backup_group",
        #replace   => "false",
        mode      => '755',
        content   => template('cloudbackup/backupscripts/test_s3_connection.py')
    }


  file { 'create_cloudbackup_logs_directory':
    path     =>  '/var/log/cloudbackup',
    ensure   =>  directory,
    owner    =>  "$backup_user",
    group    =>  "$backup_group",
    mode     =>  '755'
  }

    file { 'cloudbackup_logrotate':
        path      => "/etc/logrotate.d/cloudbackup",
        owner     => "root",
        group     => "root",
        mode      => '0440',
        content   => template('cloudbackup/cloudbackup_logrotate')
    }

}