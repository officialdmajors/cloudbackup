#!/usr/bin/env python
# WARNING: This file is managed by Puppet. Changes to this file will be overwritten.
# Script Location: /usr/share/dmajors/cloudbackup/gmp_version_checker.py
import ctypes
import os.path

### If installed by the cloudbackup puppet module
### gmp library module is installed in the '/usr/local/lib/' dir.
### so_name='/usr/local/lib/libgmp.so'
### If installed by yum(yum install gmp-devel), the
### gmp library module is installed in the '/usr/lib64/' dir.
### so_name='/usr/lib64/libgmp.so'
so_name = ['/usr/local/lib/libgmp.so', '/usr/lib64/libgmp.so' ]

### Redhat verison of the gmp library on rhel6 is in version 4.x.x
### We require the version >= 5. And thats what the cloudbackup
### puppet module installs.
for x in so_name:
    if os.path.isfile(x):
        var_name='__gmp_version'
        try:
            L=ctypes.cdll.LoadLibrary(x)
            v=ctypes.c_char_p.in_dll(L,var_name)   # this holds the version object.
            version = v.value[0]                   # this holds the version string - i have extracted just the major version number here.
            # print(v.value[0])
        except OSError:
            print('OSError: Path(supposedly having the gmp library): ' + str(x) + ' does not exist.')
        except :
            print('Unknown Exception: Something went wrong')
        else:
            if int(version) >= 5:
                print('Desired version'  + str("(>=5)") + ' of gmp package is installed - path: ' + str(x) )
                exit(0)
            else:
                print('The version' + '(' + str(version) + ')' ' of gmp library on path: ' + str(x) +  ' is not the desired version' + str("(>=5)") + '.')
    else:
        print('Path(supposedly having the gmp library): ' + str(x) + ' does not exist.' )

exit(4)
