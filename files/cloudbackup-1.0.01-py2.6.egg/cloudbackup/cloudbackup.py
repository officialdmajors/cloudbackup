#!/usr/bin/python
# EASY-INSTALL-ENTRY-SCRIPT: 'cloudbackup==1.0.01','console_scripts','cloudbackup'
# WARNING: This file is managed by Puppet. Changes to this file will be overwritten.
# Script Location: /usr/bin/cloudbackup
# File Mode: 755


__requires__ = 'cloudbackup==1.0.01'
import sys
from pkg_resources import load_entry_point

if __name__ == '__main__':
    sys.exit(
        load_entry_point('cloudbackup==1.0.01', 'console_scripts', 'cloudbackup')()
    )

