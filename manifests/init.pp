class cloudbackup (
  
  $data_paths_to_backup                  = hiera('data_paths_to_backup','nil'),
  $backup_home_dir                       = hiera('backup_home_dir','/usr/share/dmajors/cloudbackup'),
  $backup_tmp_dir                        = hiera('backup_tmp_dir', nil),
  $backup_group                          = hiera('backup_group','root'),
  $backup_gid                            = hiera('backup_gid','15072'),
  $backup_uid                            = hiera('backup_uid','15072'),
  $backup_user                           = hiera('backup_user','root'),
  $access_key                            = hiera('access_key', nil),
  $default_destination                   = hiera('default_destination', 's3'),
  $secret_key                            = hiera('secret_key', nil),
  $glacier_backup                        = hiera('glacier_backup', 'false'),
  $s3_backup                             = hiera('s3_backup', 'true'),
  $s3_bucket_name                        = hiera('s3_bucket_name' , nil),
  $glacier_vault_name                    = hiera('glacier_vault_name', nil),
  $s3_bucket_region_name                 = hiera('s3_bucket_region_name', nil),
  $glacier_vault_region_name             = hiera('glacier_vault_region_name', nil),
  $region_name                           = hiera('region_name', nil),
  $glacier_access_key                    = hiera('glacier_access_key', nil),
  $s3_access_key                         = hiera('s3_access_key', nil),
  $glacier_secret_key                    = hiera('glacier_secret_key', nil),
  $s3_secret_key                         = hiera('s3_secret_key', nil),
  $public_keyid                          = hiera('public_keyid', 'nil'),
  $gpg_key_dir                           = hiera('gpg_key_dir',  'nil'),
  $compress_backups                      = hiera('compress_backups', 'false'),

){


  class { '::cloudbackup::installclitools':
    data_paths_to_backup           =>  "${data_paths_to_backup}",
    compress_backups               =>  "${compress_backups}",
    backup_home_dir                =>  "${backup_home_dir}",
    backup_tmp_dir                 =>  "${backup_tmp_dir}",
    backup_group                   =>  "${backup_group}",
    backup_gid                     =>  "${backup_gid}",
    backup_uid                     =>  "${backup_uid}",
    backup_user                    =>  "${backup_user}",
    access_key                     =>  "${access_key}",
    region_name                    =>  "${region_name}",
    default_destination            =>  "${default_destination}",
    secret_key                     =>  "${secret_key}",
    glacier_vault_name             =>  "${glacier_vault_name}",
    s3_bucket_name                 =>  "${s3_bucket_name}",
    s3_backup                      =>  "${s3_backup}",
    glacier_backup                 =>  "${glacier_backup}",
    s3_bucket_region_name          =>  "${s3_bucket_region_name}",
    glacier_vault_region_name      =>  "${glacier_vault_region_name}",
    s3_secret_key                  =>  "${s3_secret_key}",
    glacier_secret_key             =>  "${glacier_secret_key}",
    glacier_access_key             =>  "${glacier_access_key}",
    s3_access_key                  =>  "${s3_access_key}",
    public_keyid                   =>  "${public_keyid}",
    gpg_key_dir                    =>  "${gpg_key_dir}",

  }



  class { '::cloudbackup::schedulebackup':
    data_paths_to_backup           =>  "${data_paths_to_backup}",
    backup_home_dir                =>  "${backup_home_dir}",
    backup_user                    =>  "${backup_user}",
    backup_group                   =>  "${backup_group}",
    require                        =>  Class['::cloudbackup::installclitools'];

  }








}
