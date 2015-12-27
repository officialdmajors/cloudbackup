class cloudbackup::installclitools (
  $data_paths_to_backup, $backup_home_dir, $backup_tmp_dir, $backup_group,
  $backup_gid, $backup_uid, $backup_user, $access_key,
  $default_destination, $s3_bucket_name, $secret_key,$glacier_vault_name,
  $s3_backup, $glacier_backup, $region_name, $s3_access_key, $glacier_access_key,
  $glacier_secret_key, $s3_secret_key, $glacier_vault_region_name,
  $s3_bucket_region_name, $public_keyid, $gpg_key_dir, $compress_backups

){

### Create Directories 1########
  file { 'create_backup_home_directory':
    path     =>  '/usr/share/dmajors/cloudbackup',
    ensure   =>  directory,
    owner    =>  "$backup_user",
    group    =>  "$backup_group",
    mode     =>  '775'
  }
################################

######## Create User Backups ###########
  if ( $backup_group != "root" ) and ($backup_user != "root") {
    group { "$backup_group":
      ensure    =>  present,
      gid       =>  "$backup_gid";
    }
    user { "$backup_user":
      ensure     =>  present,
      home       =>  "$backup_home_dir",
      gid        =>  "$backup_group",
      uid        =>  "$backup_uid",
      shell      =>  "/bin/bash",
      require    =>  [ Group["$backup_group"], File['create_backup_home_directory'] ];
    }
  }
########################################

### Create Directories 2########

  file { 'create_cloudbackup_container_directory':
    path     =>  '/usr/lib/python2.6/site-packages/cloudbackup-1.0.01-py2.6.egg',
    ensure   =>  directory,
    owner    =>  "$backup_user",
    group    =>  "$backup_group",
    mode     =>  '755'
  }
  file { 'create_cloudbackup_python_script_directory':
    path     =>  '/usr/lib/python2.6/site-packages/cloudbackup-1.0.01-py2.6.egg/cloudbackup',
    ensure   =>  directory,
    owner    =>  "$backup_user",
    group    =>  "$backup_group",
    mode     =>  '755'
  }
  file { 'create_cloudbackup_egg_info_directory':
    path     =>  '/usr/lib/python2.6/site-packages/cloudbackup-1.0.01-py2.6.egg/EGG-INFO',
    ensure   =>  directory,
    owner    =>  "$backup_user",
    group    =>  "$backup_group",
    mode     =>  '755'
  }
 file { 'create_gpg_directory':
    path     =>  '/usr/share/dmajors/cloudbackup/.gnupg',
    ensure   =>  directory,
    owner    =>  "$backup_user",
    group    =>  "$backup_group",
    mode     =>  '755',
    require   => File['create_backup_home_directory'] ;
 }



################################

## Lets Drop Files and Work on them ###
  #### Lets drop gpg public key ####
  file { 'gpg_pubring':
    path      => '/usr/share/dmajors/cloudbackup/.gnupg/pubring.gpg',
    owner     => "$backup_user",
    group     => "$backup_group",
    mode      => '775',
    source    => 'puppet:///modules/cloudbackup/gpg/pubring.gpg',
    require   => File['create_gpg_directory'] ;
  }

  file { 'gpg_seed':
    path      => '/usr/share/dmajors/cloudbackup/.gnupg/random_seed',
    owner     => "$backup_user",
    group     => "$backup_group",
    mode      => '775',
    source    => 'puppet:///modules/cloudbackup/gpg/random_seed',
    require   => File['create_gpg_directory'] ;
  }

  file { 'gpg_secring':
    path      => '/usr/share/dmajors/cloudbackup/.gnupg/secring.gpg',
    owner     => "$backup_user",
    group     => "$backup_group",
    mode      => '775',
    source    => 'puppet:///modules/cloudbackup/gpg/secring.gpg',
    require   => File['create_gpg_directory'] ;
  }

  file { 'gpg_trustdb':
    path      => '/usr/share/dmajors/cloudbackup/.gnupg/trustdb.gpg',
    owner     => "$backup_user",
    group     => "$backup_group",
    mode      => '775',
    source    => 'puppet:///modules/cloudbackup/gpg/trustdb.gpg',
    require   => File['create_gpg_directory'] ;
  }


  if ($backup_user == 'root') {
    file { 'cloudbackup_conf_file':
      path      => "/$backup_user/.cloudbackup.yml",
      owner     => "$backup_user",
      group     => "$backup_group",
#     replace   => "false",
      mode      => '644',
      content   => template('cloudbackup/dot_cloudbackup.yml')
    }
  } else {
    file { 'cloudbackup_conf_file':
      path      => "/home/$backup_user/.cloudbackup.yml",
      owner     => "$backup_user",
      group     => "$backup_group",
      # replace   => "false",
      mode      => '644',
      content   => template('cloudbackup/dot_cloudbackup.yml')
    }

  }




  file { 'gmp_version_checker':
    path      => '/usr/share/dmajors/cloudbackup/gmp_version_checker.py',
    owner     => "$backup_user",
    group     => "$backup_group",
    mode      => '775',
    source    => 'puppet:///modules/cloudbackup/gmp_version_checker.py',
    require   => File['create_backup_home_directory'] ;
  }

  file { 'cloudbackup_command':
    path      => '/usr/bin/cloudbackup',
    owner     => "$backup_user",
    group     => "$backup_group",
    mode      => '755',
    source    => 'puppet:///modules/cloudbackup/cloudbackup-1.0.01-py2.6.egg/cloudbackup/cloudbackup.py';
  }

  file { 'cloudbackup_init':
    path      => '/usr/lib/python2.6/site-packages/cloudbackup-1.0.01-py2.6.egg/cloudbackup/__init__.py',
    owner     => "$backup_user",
    group     => "$backup_group",
    mode      => '755',
    source    => 'puppet:///modules/cloudbackup/cloudbackup-1.0.01-py2.6.egg/cloudbackup/init.py',
    require   => File['create_cloudbackup_python_script_directory'];
  }

  file { 'cloudbackup_backends':
    path      => '/usr/lib/python2.6/site-packages/cloudbackup-1.0.01-py2.6.egg/cloudbackup/backends.py',
    owner     => "$backup_user",
    group     => "$backup_group",
    mode      => '755',
    source    => 'puppet:///modules/cloudbackup/cloudbackup-1.0.01-py2.6.egg/cloudbackup/backends.py',
    require   => File['create_cloudbackup_python_script_directory'];
  }

  file { 'cloudbackup_conf':
    path      => '/usr/lib/python2.6/site-packages/cloudbackup-1.0.01-py2.6.egg/cloudbackup/conf.py',
    owner     => "$backup_user",
    group     => "$backup_group",
    mode      => '755',
    source    => 'puppet:///modules/cloudbackup/cloudbackup-1.0.01-py2.6.egg/cloudbackup/conf.py',
    require   => File['create_cloudbackup_python_script_directory'];
  }

  file { 'cloudbackup_models':
    path      => '/usr/lib/python2.6/site-packages/cloudbackup-1.0.01-py2.6.egg/cloudbackup/models.py',
    owner     => "$backup_user",
    group     => "$backup_group",
    mode      => '755',
    source    => 'puppet:///modules/cloudbackup/cloudbackup-1.0.01-py2.6.egg/cloudbackup/models.py',
    require   => File['create_cloudbackup_python_script_directory'];
  }


  file { 'cloudbackup_plugin':
    path      => '/usr/lib/python2.6/site-packages/cloudbackup-1.0.01-py2.6.egg/cloudbackup/plugin.py',
    owner     => "$backup_user",
    group     => "$backup_group",
    mode      => '755',
    source    => 'puppet:///modules/cloudbackup/cloudbackup-1.0.01-py2.6.egg/cloudbackup/plugin.py',
    require   => File['create_cloudbackup_python_script_directory'];
  }

####### EGG INFO FILES - These can go(Not important) #########
  file { 'cloudbackup_dependency_links':
    path      => '/usr/lib/python2.6/site-packages/cloudbackup-1.0.01-py2.6.egg/EGG-INFO/dependency_links.txt',
    owner     => "$backup_user",
    group     => "$backup_group",
    mode      => '644',
    source    => 'puppet:///modules/cloudbackup/cloudbackup-1.0.01-py2.6.egg/EGG-INFO/dependency_links.txt';
  }

  file { 'cloudbackup_entry_points':
    path      => '/usr/lib/python2.6/site-packages/cloudbackup-1.0.01-py2.6.egg/EGG-INFO/entry_points.txt',
    owner     => "$backup_user",
    group     => "$backup_group",
    mode      => '644',
    source    => 'puppet:///modules/cloudbackup/cloudbackup-1.0.01-py2.6.egg/EGG-INFO/entry_points.txt';
  }

  file { 'cloudbackup_not_zip_safe':
    path      => '/usr/lib/python2.6/site-packages/cloudbackup-1.0.01-py2.6.egg/EGG-INFO/not-zip-safe',
    owner     => "$backup_user",
    group     => "$backup_group",
    mode      => '644',
    source    => 'puppet:///modules/cloudbackup/cloudbackup-1.0.01-py2.6.egg/EGG-INFO/not-zip-safe';
  }

  file { 'cloudbackup_pkg_info':
    path      => '/usr/lib/python2.6/site-packages/cloudbackup-1.0.01-py2.6.egg/EGG-INFO/PKG-INFO',
    owner     => "$backup_user",
    group     => "$backup_group",
    mode      => '644',
    source    => 'puppet:///modules/cloudbackup/cloudbackup-1.0.01-py2.6.egg/EGG-INFO/PKG-INFO';
  }

  file { 'cloudbackup_sources':
    path      => '/usr/lib/python2.6/site-packages/cloudbackup-1.0.01-py2.6.egg/EGG-INFO/SOURCES.txt',
    owner     => "$backup_user",
    group     => "$backup_group",
    mode      => '644',
    source    => 'puppet:///modules/cloudbackup/cloudbackup-1.0.01-py2.6.egg/EGG-INFO/SOURCES.txt';
  }

  file { 'cloudbackup_top_level':
    path      => '/usr/lib/python2.6/site-packages/cloudbackup-1.0.01-py2.6.egg/EGG-INFO/top_level.txt',
    owner     => "$backup_user",
    group     => "$backup_group",
    mode      => '644',
    source    => 'puppet:///modules/cloudbackup/cloudbackup-1.0.01-py2.6.egg/EGG-INFO/top_level.txt';
  }
##############################################################


  file { 'gmp_installer_script':
    path      => '/usr/share/dmajors/cloudbackup/gmp_installer.sh',
    owner     => "$backup_user",
    group     => "$backup_group",
    mode      => '775',
    source    => 'puppet:///modules/cloudbackup/gmp_installer.sh',
    require   => File['create_backup_home_directory'] ;
  }

  exec {'install_gmp_library':
    command => "/usr/share/dmajors/cloudbackup/gmp_installer.sh",
    unless => "/usr/share/dmajors/cloudbackup/gmp_version_checker.py",
    require   =>[ File['gmp_version_checker'],  File['gmp_installer_script'], Exec['explode_gmp_tar_binaries'], Package['python-pip']  ];
  }

  file { 'deploy_gmp_binaries_tar':
    path      => '/usr/share/dmajors/cloudbackup/gmp-6.0.0a.tar.bz2',
    owner     => "$backup_user",
    group     => "$backup_group",
    mode      => '775',
    source    => 'puppet:///modules/cloudbackup/gmp-6.0.0a.tar.bz2',
    require   =>  File['gmp_version_checker'];
  }
  exec { 'explode_gmp_tar_binaries':
    command     => "/bin/tar -xvjpf    /usr/share/dmajors/cloudbackup/gmp-6.0.0a.tar.bz2   -C /usr/share/dmajors/cloudbackup/",
    unless      => "/usr/bin/test   -d   /usr/share/dmajors/cloudbackup/gmp-6.0.0",
    require     => File['deploy_gmp_binaries_tar'];
  }

######################

### Install packages ########

  satellitesubscribe{"awss3-tools-epel": channel_name => 'epel'}

   yumgroup {'Development tools': ensure => present,
      require =>  Satellitesubscribe['awss3-tools-epel'];
   }
  package { 'gcc': ensure => present,
   require =>  Satellitesubscribe['awss3-tools-epel'];
  }

  package {
    'python-devel': ensure => present,
     require => Package['gcc'];
###     require => Yumgroup['Development tools'];
    'libyaml-devel': ensure => present,
     require => Package['python-devel'];
    'libyaml': ensure => present,
     require => Package['libyaml-devel'];
    'python-pip': ensure => present,
     require => Package['libyaml-devel'];
    'python-setuptools': ensure => present,
     require => Package['python-pip'];
   }
  package { 'argparse': ensure => installed, provider => 'pip',
  require => Package['python-pip'];}
  package { 'importlib': ensure => installed, provider => 'pip',
  require => Package['python-pip'];}
  package { 'pycrypto': ensure => latest, provider => 'pip',
    require => [ Package['argparse'], Package['importlib'],  Exec['install_gmp_library'] ]  ;
  }
  package { 'sh': ensure => installed, provider => 'pip',
  require => Package['pycrypto'];}

  package { 'gnupg': ensure => installed, provider => 'pip',
  require => Package['pycrypto'];}

  package { 'events': ensure => installed, provider => 'pip',
  require => Package['pycrypto'];}

  package { 'aaargh': ensure => installed, provider => 'pip',
  require => Package['pycrypto'];}

  package { 'boto': ensure => installed, provider => 'pip',
  require => Package['pycrypto'];}

  package { 'psutil': ensure => installed, provider => 'pip',
  require => Package['pycrypto'];}

  package { 'beefish': ensure => installed, provider => 'pip',
  require => Package['pycrypto'];}

  package { 'GrandFatherSon': ensure => installed, provider => 'pip',
  require => Package['pycrypto'];}

  package { 'peewee': ensure => installed, provider => 'pip',
  require => Package['pycrypto'];}

  package { 'byteformat': ensure => installed, provider => 'pip',
  require => Package['pycrypto'];}

  package { 'pyyaml': ensure => installed, provider => 'pip',
  require => Package['pycrypto'];}

  package { 'requests': ensure => installed, provider => 'pip',
  require => Package['pycrypto'];}

  package { 'filechunkio': ensure => installed, provider => 'pip',
  require => Package['pycrypto'];}
  package { 'iso8601': ensure => installed, provider => 'pip',
  require => Package['pycrypto'];}
  package { 'pytz': ensure => installed, provider => 'pip',
  require => Package['pycrypto'];}

################################





}