import subprocess
import boto
from boto.s3.key import Key
from boto.glacier.exceptions import UnexpectedHTTPResponseError
from boto.exception import S3ResponseError
from cloudbackup.conf import config, CONFIG_FILE


recipient = 'officialdmajors@gmail.com'
subject = 'test mail 1001'
body = 'testing mail through python'

def send_message(recipient, subject, body):
    try:
      process = subprocess.Popen(['mail', '-s', subject, recipient],
                                close_fds=True,
                               stdin=subprocess.PIPE)
    except Exception, error:
      print error
      process.kill()
    process.communicate(body)
    process.wait()

send_message(recipient, subject, body)

print("sent the email")


def return_rotation_policy_dict():
    # day_to_seconds = 86400        # 1 day has 86400
    # month_to_seconds = 2592000    # 30 days
    # year_to_seconds = 31536000    # 365 days
    # rotation_policy_dict = { s:1, m:60, h:3600, D:86400, W:604800, M:2592000, Y:31536000 }
    #return  { "daily":7, "weekly":28, "monthly":336, "yearly":365 }
    return  { "d":7, "w":28, "m":336, "y":365 }