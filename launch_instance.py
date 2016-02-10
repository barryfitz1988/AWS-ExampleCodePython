import sys
import time
import boto
import boto.ec2

# Stephen Murray

#This script create a new AMI image - the user is prompted for the following
#   userEnteredAMI - OS for the machine, Windows or Linux
#   userEnteredInstanceName - AMI Name
#   userEnteredKeyName - The name of the key which you use for getting the machine password
# We use the run_instances function to pass the OS, key value, type(we are free-tier) and the security group.  We can just
# use the standard security group.  If successful we should get a boto.ec2.instance.Reservation object returned to us.
# Because the run_instances() offers no way to set the instance name we use the reservation to access the instance and
# set the name.  We then print out the instance id that was created.

windowsAMI = "ami-6e7bd919"
LinuxAMI = "ami-d4228ea3"

reg = boto.ec2.get_region("eu-west-1")
connAWS = boto.connect_ec2(region=reg)

while True:
    userEnteredAMI = str(raw_input("Please enter whether you want a Windows or Linux AMI - Q will allow you to exit: "))
    
    if not(userEnteredAMI == "Windows" or userEnteredAMI == "Linux" or userEnteredAMI == "Q"):
        print("Invalid entry try again")
        continue
    else:
        if (userEnteredAMI == 'Q'):
            print "Exiting..."
            sys.exit()
        break

userEnteredInstanceName = str(raw_input("Please enter AMI Instance Name: "))

userEnteredKeyName = str(raw_input("Please enter key name (the one with the .pem extension!!: "))

imageID = windowsAMI if (userEnteredAMI == "Windows") else LinuxAMI                                        

try:
    res = connAWS.run_instances(image_id = imageID, key_name=userEnteredKeyName, instance_type='t2.micro', security_groups=['default'])
except Exception as e:
    print "Error with instance creation.  Check arguments and try again. Exiting..."

#We wait 3 seconds just to give the web service a chance to create and launch machine
time.sleep(3)                                   
res.instances[0].add_tag('Name', userEnteredInstanceName)
                                        
print "AMI created.  Instance ID", res.instances[0].id
    

                                        



