#!/usr/bin/env python
import logging
import sys

# Testing S3 connectivity #
# Stage 1: Check if you can connect to S3
# Stage 2: Check if you can create a bucket
# Stage 3: Check if you can upload a file to the bucket.

"""

def push_picture_to_s3():

  try:
    import boto
    from boto.s3.key import Key
    # set boto lib debug to critical
    #logging.getLogger('boto').setLevel(logging.CRITICAL)
    bucket_name = BUCKET_NAME
    # connect to the bucket
    conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    bucket = conn.get_bucket(bucket_name)

    # go through each version of the file
    #key = '%s.png' % id
    file_n = 'okeke'
    #fn = '/var/www/data/%s.png' % id

    # create a key to keep track of our file in the storage
    print("create a key to keep track of our file in the storage")
    k = Key(bucket)
    k.key = file_n
    k.set_metadata('meta1', 'This is the first metadata value')
    k.set_metadata('meta2', 'This is the second metadata value')
    # We upload the file now.
    k.set_contents_from_filename(file_n)
    k.set_acl("private")
    # here we download the file to a different file name called barsin.
    k.get_contents_to_filename('barsin')

    # we need to make it public so it can be accessed publicly
    # using a URL like http://s3.amazonaws.com/bucket_name/key
    # k.make_public()
    # remove the file from the web server
    # os.remove(fn)
    bucket_list = bucket.list()
    print('S3 object contents in bucket [', BUCKET_NAME, ']: ')
    for l in bucket_list:
        keyString = str(l.key)
        print(keyString)

  except:
    print(sys.exc_info())

push_picture_to_s3()
"""