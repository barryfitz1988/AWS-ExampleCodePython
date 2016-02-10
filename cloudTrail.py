
# Stephen Murray 

#CloudTrail is a web service that records AWS API calls for your AWS account and delivers log files to an Amazon S3 bucket. The
# recorded information includes the identity of the user, the start time of the AWS API call, the source IP address, the request
# parameters, and the response elements returned by the service.  There is NO additional charge for CloudTrail, but standard
# rates for Amazon S3 and Amazon SNS usage apply.
# You must ensure that CloudTrail has permission to access the bucket, guide here: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/create_trail_bucket_policy.html
# When it is working you will see a file at a path similar to the following //smbucketcit1/AWSLogs/135577527805/CloudTrail/eu-west-1/2014/10/31
# At that location there will be one ot more json.gz files - Log files are written in JSON (JavaScript Object Notation) format - you can view them from browser
# or alternatively you can download them and open in editor that has a JSON plug-in
# The four methods used are marked in the code at the end of the line..#Method #x
# The user is prompted for the Bucket Name and Trail Name

#First Connect to Cloud Trail Service
import sys
import boto
import boto.cloudtrail

ct = boto.cloudtrail.connect_to_region("eu-west-1")

#Prompt user for bucket.  We get a list of the current buckets and ensure what the user has entered is present in our bucket list
connS3 = boto.connect_s3()
rs = connS3.get_all_buckets()

bucketList = []
for b in rs:
    bucketList.append(b.name)

while True:
    userEnteredBucket = str(raw_input("Please enter bucket name - Q will allow you to exit: "))

    if (userEnteredBucket == 'Q'):
        sys.exit()
    elif  userEnteredBucket in bucketList:
        break
    else:
        print "Invalid bucket please use one of: "
        for b in bucketList:
            print b
        continue

#Prompt user for trail name
userEnteredTrail = str(raw_input("Please enter trail name: "))
   

#Create the trail - you will get a dict on return
# Example return object: {u'trailList': [{u'IncludeGlobalServiceEvents': False, u'Name': u'CloudTrailSMTst', u'S3BucketName': u'smbucketcit1'}]}
# We use a try here in case there is an error with trail creation - for example the trail could already exist, bucket can have only one trail etc.
try:
    ct.create_trail(trail={'Name': userEnteredTrail, 'S3BucketName': userEnteredBucket}) #Method #1
except Exception as e:
    print "Error with trail creation.  Check trail doesn't already exist. Exiting..."
    sys.exit()

#Update to turn off global events
#u'IncludeGlobalServiceEvents': True is u'IncludeGlobalServiceEvents': False
ct.update_trail(trail={'Name': userEnteredTrail, 'IncludeGlobalServiceEvents': False}) #Method #2

#Start Logging
ct.start_logging("CloudTrailSMTst") #Method #3

#Describe Trails
trails = ct.describe_trails() #Method #4

#Print out some info
print "Details of Cloud Trail just created:"
print "Name: ", trails["trailList"][0]['Name']
print "S3BucketName: ", trails["trailList"][0]['S3BucketName']
print "IncludeGlobalServiceEvents: ", trails["trailList"][0]['IncludeGlobalServiceEvents']
