# -*- encoding: utf-8 -*-
# WARNING: This file is managed by Puppet. Changes to this file will be overwritten.
# Script Location: /usr/lib/python2.6/site-packages/cloudbackup-1.0.01-py2.6.egg/cloudbackup/conf.py
# File Mode: 755
import yaml
import os
import logging
import sys
import gnupg     # Used to encrypt generated password.
import distutils.dir_util
from events import Events

from os import urandom
from random import choice
from events import Events

log = logging.getLogger(__name__)

GPG_LANDING_DIR = '/usr/share/dmajors/cloudbackup/.gnupg'
CONFIG_FILE = os.path.expanduser("~/.cloudbackup.yml")
PLUGINS_DIR = os.path.expanduser("~/.cloudbackup_plugins")
DATABASE = os.path.expanduser("~/.cloudbackup.sqlite")
DEFAULT_GPG_KEY_DIR = os.path.expanduser("~/.gnupg")
DEFAULT_PUBLIC_KEYID = 'officialdmajors@gmail.com'
DEFAULT_LOCATION = "us-east-1"
DEFAULT_DESTINATION = "s3"


def copy(src, dest):
    try:
       # Recursively copy all file & folders in src to dest
       # dest is created if it does not exist.
       # if src does not exists, nothing happens.
       distutils.dir_util.copy_tree(src, dest)
    except :
        # if an error occurs(eg permission denied) error & exit.
        raise

def load_config(config_file=CONFIG_FILE):
    """ Try to load a yaml config file. """
    config = {}
    if os.path.isfile(config_file):
        log.debug("Try loading config file: {0}".format(config_file))
        try:
            config = yaml.load(open(config_file))
        except:
            log.debug('Storage configuration file is not a "true" yaml file!')
            pass
        if config:
            log.debug("Config loaded")
        else:
            print('OUT: Storage configuration not loaded!')
            print('OUT: Please examine configuration file: ['  + str(config_file) + ']' )
            print('OUT: Unable to proceed with your request. Exiting!...')
            sys.exit()
    else:
        print('OUT: Storage configuration file: [' + str(config_file) + '] is missing!')
        print('OUT: Unable to proceed with your request. Exiting!...')
        sys.exit()
    return config







# Read default config file
config = load_config()
events = Events()   # database events
dict_conf = config.get('default', {})
TEMPORARY_DIR = dict_conf.get("tmp_dir", 'nil')

# Not needed in cloudbackup 1.0.01. Stays for future use case.
def set_tmp_dir():
    if TEMPORARY_DIR != 'nil':
        if os.path.isdir(TEMPORARY_DIR):
            return TEMPORARY_DIR
        else:
            return None
    else:
        return None


##### Lets Generate Random passwords to use for encryption ######
char_set = {'small': 'abcdefghijklmnopqrstuvwxyz',
             'nums': '0123456789',
             'big': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            }

def generate_pass(length=21):
    """Function to generate random password"""
    password = []
    while len(password) < length:
        key = choice(char_set.keys())
        a_char = urandom(1)
        if a_char in char_set[key]:
            if check_prev_char(password, char_set[key]):
                continue
            else:
                password.append(a_char)
    return ''.join(password)

def check_prev_char(password, current_char_set):
    """Function to ensure that there are no consecutive
    UPPERCASE/lowercase/numbers/special-characters."""
    index = len(password)
    if index == 0:
        return False
    else:
        prev_char = password[index - 1]
        if prev_char in current_char_set:
            return True
        else:
            return False

PASSWORD_4_ENCRYPTION = generate_pass()
###################################################
################# Lets encrypt the password generated ##############
  ########### using gpg public key with default id ############
   ####### DEFAULT_PUBLIC_KEYID = 'officialdmajors@gmail.com' ########
def encrypt_generated_pass(passphrase, gpgdir=DEFAULT_GPG_KEY_DIR, default_public_keyid=DEFAULT_PUBLIC_KEYID):
    conf =  config.get('default')
    if config['default']['gpg_key_dir']  != 'nil' and config['default']['gpg_key_dir'] != '' :
        gpgdir = config['default']['gpg_key_dir']

    if config['default']['public_keyid']  != 'nil' and config['default']['public_keyid'] != '' :
        gpgdir = config['default']['public_keyid']

    #### Lets copy gpg public key to user home directory #####
    if not os.path.isdir(gpgdir):
        try:
            os.makedirs(gpgdir)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                log.error("ERROR: Please check that you can create directory[", gpgdir , "].")
                raise


    if os.path.isdir(GPG_LANDING_DIR):
        copy(GPG_LANDING_DIR, gpgdir)



    try:
        gpg = gnupg.GPG(homedir=gpgdir)
        unencrypted_string = passphrase
        encrypted_data = gpg.encrypt(unencrypted_string, default_public_keyid)
        encrypted_string = str(encrypted_data)
    except:
        log.error("ERROR: Please check that you have public key set up in DIR - [", gpgdir, "]")
    return encrypted_string


def decrypt_encrypted_pass_file(encrypted_pass_file_name, gpgdir=DEFAULT_GPG_KEY_DIR, default_public_keyid=DEFAULT_PUBLIC_KEYID):
    conf =  config.get('default')
    if config['default']['gpg_key_dir']  != 'nil' and config['default']['gpg_key_dir'] != '' :
        gpgdir = config['default']['gpg_key_dir']

    if config['default']['public_keyid']  != 'nil' and config['default']['public_keyid'] != '' :
        gpgdir = config['default']['public_keyid']

    #### Lets copy gpg public key to user home directory #####
    if not os.path.isdir(gpgdir):
        try:
            os.makedirs(gpgdir)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                log.error("ERROR: Please check that you can create directory[", gpgdir , "].")
                raise

    try:
        gpg = gnupg.GPG(homedir=gpgdir)
        with open(encrypted_pass_file_name, 'rb') as fh:
            decrypted_data = gpg.decrypt_file(fh)
            decrypted_string = str(decrypted_data)
    except:
        log.error("ERROR: Please check that you have your gpg public & private key set up in DIR - [", gpgdir, "]")
        raise
    return decrypted_string


###################################################################


