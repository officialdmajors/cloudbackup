#!/usr/bin/env bash
# WARNING: This file is managed by Puppet. Changes to this file will be overwritten.
# Script Location: /usr/share/dmajors/cloudbackup/gmp_installer.sh


### Declare Variables: #####
SCRIPT_NAME=$( basename $0 )
export DATE_TIME=`date "+%d-%m-%Y %H:%M:%S"`
gmp_source_directory='/usr/share/dmajors/cloudbackup/gmp-6.0.0'
log_file='/usr/share/dmajors/cloudbackup/gmp_install_log'
gmp_version_checker='/usr/share/dmajors/cloudbackup/gmp_version_checker.py'
############################
####### Function Definition ###########
function run_command_and_check_for_errors () {
DATE=$( date +%H:%M:%S:%d%m%Y )
## 1st argument to this fuction is the command to execute
$1   | tee -a   ${log_file}   2>&1

if test $? -gt 0; then
 echo "$DATE failed command ==> [ $1 ]"
## 2nd argument to this function takes value 1 if you want logging to a file
   if test $2 -eq 1; then
      echo "$DATE failed command ==> [ $1 ]"  >>  ${log_file}   2>&1
      if test $3 -eq 1; then
       echo "$DATE Script:[ ${SCRIPT_NAME} ] run is aborted. {Last failed command executed: [$1] }"     | tee -a   ${log_file}   2>&1
       exit
      fi
   fi
## 3rd argument to this function takes value 1 or 0: 1 to kill the script, 0 to continue its run.
else
   echo "$DATE successful command ==> [ $1 ]"
   if test $2 -eq 1; then
      echo "$DATE successful command ==> [ $1 ]"  >> ${log_file}   2>&1
   fi
fi

}
#######################################

#### Pay Load ####
if /usr/bin/test   -x   ${gmp_version_checker}; then
     echo "Date: ${DATE_TIME} - The GMP library version checker script( ${gmp_version_checker} ) exists and is executable."     | tee -a   ${log_file}   2>&1
     ${gmp_version_checker}
     if test $? -eq 0; then
        echo "Date: ${DATE_TIME} - The GMP library is installed with the recommended version."     | tee -a   ${log_file}   2>&1
        echo "Date: ${DATE_TIME} - Script:[ ${SCRIPT_NAME} ] run has a clean exit."     | tee -a   ${log_file}   2>&1
        exit
     else
        echo "Date: ${DATE_TIME} - The GMP library may not be installed. Proceeding with the installation."     | tee -a   ${log_file}   2>&1
     fi
else
    echo "Date: ${DATE_TIME} - Check that the GMP library version checker script( ${gmp_version_checker} ) exists and is executable - exiting..."     | tee -a   ${log_file}   2>&1
    echo "Date: ${DATE_TIME} - Script:[ ${SCRIPT_NAME} ] run is aborted."     | tee -a   ${log_file}   2>&1
    exit
fi

if /usr/bin/test   -d   ${gmp_source_directory}; then
    echo "Date: ${DATE_TIME} - GMP library directory found"      | tee -a   ${log_file}   2>&1
else
    echo "Date: ${DATE_TIME} - GMP library directory( ${gmp_source_directory} ) NOT found - exiting..."     | tee -a   ${log_file}   2>&1
    exit
fi
######## Actual Configure, make and make install  ####
cd ${gmp_source_directory}
echo -e  "\n\nDate: ${DATE_TIME} - Running: configure command!\n\n"      | tee -a   ${log_file}   2>&1
run_command_and_check_for_errors "./configure" "1" "1"
echo "\n\nDate: ${DATE_TIME} - Running: make command!\n\n"               | tee -a   ${log_file}   2>&1
run_command_and_check_for_errors "make" "1" "1"
echo "\n\nDate: ${DATE_TIME} - Running: make check command!\n\n"         | tee -a   ${log_file}   2>&1
run_command_and_check_for_errors "make check" "1" "1"
echo "\n\nDate: ${DATE_TIME} - Running: make install!\n\n"               | tee -a   ${log_file}   2>&1
run_command_and_check_for_errors "make install" "1" "1"
########################################################