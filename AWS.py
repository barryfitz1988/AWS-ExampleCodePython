import sys
import boto
import socket
import random
import argparse
import boto.ec2
import boto.sns
import argparse
import validate_email
import boto.ec2.cloudwatch

# Stephen Murray

# checkInternetConnection function checks that the user has internet access before attempting to interact with AWS - its a simple method that get an IPv4 address (as a str object)
# and attempt to connect to the TCP service listening on the the host parameter,  in this case python.org.  If successful a socket object is returned - otherwise an exception
# will occur and we will exit the program
def checkInternetConnection():
    try:
        host = socket.gethostbyname("www.python.org")
        soc = socket.create_connection((host, 80), 2)
        return
    except:
     pass
    print "No internet connection detected...exiting"
    sys.exit()


#checkArgs functions ensure that the user entered the correct arguments.  -cw can only be 0 or 1.  You are only allowed to pass one of -id, -t, -r, -lt.
# You have to enter a valid email address - we have used validate_email library - setup details are in README.txt file
def checkArgs():
    if (not(args.cw == "0" or args.cw == "1")):
        print "-cw switch has to have value of 0 or 1...exiting"
        sys.exit()

    #by default checkPrintInstArgs will be False, so if only one is selected then the sum of the list elements will be 1
    if sum(checkPrintInstArgs) > 1:
        print "You have to select ONLY ONE of -id, -t, -r, -lt...exiting"
        sys.exit()

    #Note the default email address is youremail@hotmail.com - this will only fail if you enter an incorrect email address at command line
    is_validEmailAdd = validate_email.validate_email(args.email)
    if (not is_validEmailAdd):
        print "Bad email address entered...exiting"
        sys.exit()
    
#outputEC2 function will output EC2 instance information based on user input 
def outputEC2():

    #we first need to connect to Amazon EC2 - we will use the connect_ec2 method.  We don't have to supply the access ID or secret key as this is setup via,
    # a config file/environment variable what we do need to supply is the region.  You need to supply the region - you cant use a string, a class
    # boto.regioninfo.RegionInfo is required.  To find this out look at the EC2Connection class in connection.py(this is in boto package).  It checks
    # if you supplied a region - if you have not it will create a new object  region = RegionInfo(self, self.DefaultRegionName, - self.DefaultRegionEndpoint).  The default
    # region is 'us-east-1 (defined on line 76)

    reg = boto.ec2.get_region("eu-west-1")
    connAWS = boto.connect_ec2(region=reg)

    #Now we are connected.  We need to get a list of machine instances and format output for user.  get_all_instances is now deprecated in favour of get_all_reservations()
    # they both return a list of boto.ec2.instance.Reservation.  This object is not named very well and the documentation is not very clear.  There is a one one mapping
    # between instances and reservations when you use the below code.  Where reservation  object come in useful is when you start an instance using
    # conn.run_instances(...).  A reservation value is returned and can be stored containing an array that stores all the concurrently started instances
    # You can now for example use stop_all method to stop all instances

    reservations = connAWS.get_all_reservations()
    global instances
    instances = [instance for res in reservations for instance in res.instances]

    #We now have all instance - output data to user based our command line input
    print "Running AWS EC2 instances: \n"

    #Use flag to only print what switch was selected once
    printOnce = True
    
    #use enumerate - avoids having to use a counter
    for index, inst in enumerate(instances):
        #use sys.stdout.write as print gives issues with adding unnecessary spaces
		
		#Command line switch: -id ; output instance ID to user
        if (args.id):
            if (printOnce): sys.stdout.write("\t-id switch supplied\n")
            sys.stdout.write("\t" + str(index) + ": " + inst.id + '\n')
            printOnce = False
		
		#Command line switch: -t ; output type to user
        if(args.t):
            if (printOnce): sys.stdout.write("\t-t switch supplied\n")
            sys.stdout.write("\t" + str(index) + ": " + inst.instance_type + '\n')
            printOnce = False
		
		#Command line switch: -r ; output region to user
        if(args.r):
            if (printOnce): sys.stdout.write("\t-r switch supplied\n")
            sys.stdout.write("\t" + str(index) + ": " + " <RegionInfo:" + inst.region.name + ">\n")
            printOnce = False
        
		#Command line switch: -lt ; output launch time to user		
        if(args.lt):
            if (printOnce): sys.stdout.write("\t-lt switch supplied\n")
            sys.stdout.write("\t" + str(index) + ": " + " <Running Since:" +  inst.launch_time + '>\n')
            printOnce = False

        #and if none are selected the sum of checkPrintInstArgs will be 0  - output full information.
        if sum(checkPrintInstArgs) == 0:
            if (printOnce): sys.stdout.write("\tNo switch selected - show all information\n")
            sys.stdout.write("\t" + str(index) + ": " + inst.id + " - " + inst.instance_type + " <RegionInfo:" + inst.region.name + ">" + " <Running Since:" +  inst.launch_time + '>\n')
            printOnce = False
    
#outputS3 function always print S3 buckets - no command line option specified in requirements
def outputS3():    
    # First we need to connect to the Simple Storage Service.  We receive an s3.connection.S3Connection object back.  From here we have access to a method
    # that returns all buckets - get_all_buckets.  get_all_buckets() returns a ResultSet object which is a wrapper around a list object for storing data that the service sends back.
    # we can iterate through this and get our bucket names
    print "\nCurrent AWS S3 buckets: \n"

    connS3 = boto.connect_s3()
    rs = connS3.get_all_buckets()
    for b in rs:
        print "\t",b.name


#setCloudWatchState function Enables/Disables Cloud Watch Monitoring
def setCloudWatchState():
    if (args.cw == "1"):
        print "\nEnabling cloud watch"
        for inst in instances:
            inst.monitor(); #enable function
    else:
        print "\nDisabling cloud watch"
        for inst in instances:
            inst.unmonitor();#disable function
    

#alarmProcessor functions will either create new topic, subscription and alarms or delete all existing topic, subscription and alarms based on the command line switch clear.
# You cannot delete any subscription that isPendingConfirmation - Amazon haven't implemented this feature yet - which they really should as for example its quite possible to enter a
# bad email address and you now have to wait 3 days to remove it.
# Each time you run the create functions it creates NEW topic, subscription and alarms
# NB: it is cleaner that when you create new topics/subscriptions/alarms -  acknowledge the email - makes clean-up neater
def alarmProcessor():
    
	# Firstly we need to connect to the Simple Notification Service and CloudWatch service - this was a bit tricky and again the documentation was unclear.  I thought you would use boto.connect_sns(region=reg) 
	# which seems to successfully connect and is similar to how we connected to S3 and EC2 services.  However calling methods e.g. get_all_topics() yields the error "The requested version (2010-03-31) of 
	# service AmazonEC2 does not exist".  On further investigation I found that to connect use boto.sns.connect_to_region().  You have to supply the region as an argument - note that it expected a string 
	# not a region object - which again is inconsistent with EC2. To connect to the CloudWatch service as with SNS you have to use the connect_to_region() method
    sns = boto.sns.connect_to_region("eu-west-1")
    cw = boto.ec2.cloudwatch.connect_to_region("eu-west-1")
    
    if (not args.clear):
        print "\nCreating new topics (+ subscription) and alarms:\n"
        # Once connected we create a topic which is basically an access point composed of an identifier and recipients to send message to. create_topic() returns a unique ARN (Amazon Resource Name) which
        # will include the service name (SNS), region, AWS ID of the user and the topic name - this is a dict so we need to go three levels in to get the actual ARN number.  We will use the arn when
        # we create a subscription which is how we link a topic to an endpoint like an email address.

        topicName = 'TopicStephenCIT-1-UID'+str(random.randrange(1000000))
        response = sns.create_topic(topicName)
        topicARN = response['CreateTopicResponse']['CreateTopicResult']['TopicArn']
        
        print '\tTopic ARN created: ',topicARN
		
		#Subscribe links a topic with an endpoint - in this case an email address
        sns.subscribe(topicARN, 'email',  args.email)

        #We now have topic/subscription - the email address supplied will have to accept the AWS Notification Subscription Confirmation‏ email message to ensure they get alerts
        # We will now create a unique alarm per instance.  We can use the create_alarm method which expects a  boto.ec2.cloudwatch.alarm.MetricAlarm object.  This object defines 
		# all the properties of the alarm - name,metric,topic etc. We loop through all the instance and create an alarm for each instance.  Note we use the ARN that was created 
		# above which ties the alarm to notification logic
                                                   
        for index, inst in enumerate(instances):
            alarmName = "StephenMurrayCPU-" + str(index) + inst.id +'-UID' + str(random.randrange(1000000))
            alarm = boto.ec2.cloudwatch.MetricAlarm(name=alarmName, namespace='AWS/EC2',metric='CPUUtilization',
                                                    statistic='Average',comparison='<', threshold='40',period='60', evaluation_periods=2,
                                                    dimensions = {"InstanceId": inst.id},
                                                    alarm_actions= topicARN)
            cw.create_alarm(alarm)
            print "\tAlarm created", alarmName
    
    else:
        print "\nClearing topics, subscriptions (confirmed) and alarms:\n"
        
        #Get all topics
        returnAllTopicsObject = sns.get_all_topics()
        #to access the ARN field we need have to go 3 levels deep into returned object
        topics = returnAllTopicsObject['ListTopicsResponse']['ListTopicsResult']['Topics']

        #now we have a list containing dicts where the only value is the TopicArn which is what we need to supply the delete method
        # only do action if list is not empty - there has to be some topics to delete
        if topics:
            for t in (topics):
                topicARNDelete = t['TopicArn']
                #delete topics
                sns.delete_topic(topicARNDelete)
                print "\tTopic Deleted: ", topicARNDelete
        else:
            print "\tNo topics found"

        # Get all subscriptions
        # Very similar to topics - get subscriptions, extract relevant parameter from retuned dict object, loop through, get SubscriptionArn
        # and send for deletion - also do a check to ensure subscriptions exist

        returnAllSubObject = sns.get_all_subscriptions()
        #to access the Sub ARN field we need have to go 3 levels deep into returned object
        subscriptions = returnAllSubObject['ListSubscriptionsResponse']['ListSubscriptionsResult']['Subscriptions']

        if subscriptions:
            for s in (subscriptions):
                subARNDelete = s['SubscriptionArn']
                #delete subscription only if returned value is not equal to PendingConfirmation
                if (subARNDelete != 'PendingConfirmation'):
                    sns.unsubscribe(subARNDelete)
                    print "\tSunscription Deleted: ", subARNDelete
        else:
            print "\tNo subscriptions found"

        #Get all alarms
        #describe_alarms() returns a list of boto.ec2.cloudwatch.alarm.MetricAlarms object from which we can extract the alarm name (.name method) which we can
        # use to delete it - Note in this case we do not require the ARN to delete - on testing with IDLE it was noted that when a complete arn
        # arn:aws:cloudwatch:eu-west-1:135577527805:alarm:StephenMurrayCPU0i-690b332b was supplied the delete_alarms() method returned True even though it was
        # not deleted...this is not good as as when StephenMurrayCPU0i-690b332b was supplied it deleted the alarm and also returned True.

        alarms = cw.describe_alarms()
        if alarms:
            for a in (alarms):
                cw.delete_alarms(a.name)
                print "\tAlarms Deleted: ", a.name
        else:
            print "\tNo alarms found"
    
if __name__ == "__main__":

    #This logic sets up the command line arguments.  We add individual switches for instance ID, type, region and launch time.  I have also
    #added switches to disable/enable CloudWatch monitoring, to supply an email address and to clean up .
    #       You are only allowed to pass one of -id, -t, -r, -lt.
    #       Cloud Watch monitoring is enabled by default and can be disabled by passing 0 - 0 or 1 are the only allowable values
    #       The -email option allows the user to specify an email for a subscription.
    #       The clear options will clear all existing subscriptions, topics and alarms.  If the clear option is not specified then subscriptions,topics and alarm are created
    parser = argparse.ArgumentParser(description="Interact with Amazon Web Services")
    parser.add_argument("-id", action="store_true", help="instance ID")
    parser.add_argument("-t", action="store_true",help="instance type")
    parser.add_argument("-r", action="store_true", help="instance region")
    parser.add_argument("-lt", action="store_true", help="instance launch time")
    parser.add_argument("-cw", action="store", dest="cw", default= "1", required=False, help="Enable (1) Disable(0) CloudWatch")
    parser.add_argument("-email", action="store", dest="email", default= "stephen.murray30@hotmail.com", required=False, help="Email Address for CloudWatch Alarms")
    parser.add_argument("-clear", action="store_true", help="Clear topics, subscriptions and alarms - if this argument is NOT specified new topics, subscriptions and alarms be created")

    args = parser.parse_args()

    #We read in the values in to a list checkPrintInstArgs
    checkPrintInstArgs = []
    checkPrintInstArgs.extend([int(args.id),int(args.t),int(args.r),int(args.lt)])
    #Require instances in more then one function - global parameter set in outputEC2() used in setCloudWatchState()
    instances = []

    #Have used functions to make the code more readable
    checkInternetConnection()

    checkArgs()

    outputEC2()

    outputS3()

    setCloudWatchState()
    
    alarmProcessor()
    


    
