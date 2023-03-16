import boto3 
from time import sleep
from urllib import response
import boto3
from botocore.exceptions import ClientError

from CreateSnapshot import snapshot
from CreateKMS import create_kms_key
from CopySnapshot import copy_snapshot
from ShareSnapshot import share_snapshot
from CopySnapshotDestination import CopySnapshotdown
from RestoreSnapshot import restorecopiedsnapshot
from DeleteSnapshot import delete_snapshot

def lambda_handler(event, context):
    AWSRegion = event['Region']
    RDSInstance = event['RDSInstance']
    AWSSourceAccountID = event['AWSSourceAccountID']
    AWSDestinationAccountID = event['AWSDestinationAccountID']
    subnetgroup = event['subnetgroup']

    #Assume Role
    sts_client = boto3.client('sts')
    response  = sts_client.assume_role(
        RoleArn="arn:aws:iam::%s:role/Customer_Backup" % AWSSourceAccountID,
        RoleSessionName="Customer_Backup"
    )

    ACCESS_KEY = response['Credentials']['AccessKeyId']
    SECRET_KEY = response['Credentials']['SecretAccessKey']
    SESSION_TOKEN = response['Credentials']['SessionToken']

    #Calling the Functions
    snapshot(ACCESS_KEY,SECRET_KEY,SESSION_TOKEN,AWSRegion,RDSInstance)
    create_kms_key(ACCESS_KEY,SECRET_KEY,SESSION_TOKEN,AWSRegion,RDSInstance)
    copy_snapshot(ACCESS_KEY,SECRET_KEY,SESSION_TOKEN,AWSRegion,RDSInstance)
    share_snapshot(ACCESS_KEY,SECRET_KEY,SESSION_TOKEN,AWSRegion,RDSInstance,AWSDestinationAccountID)
    CopySnapshotdown(AWSRegion,RDSInstance,AWSSourceAccountID)
    restorecopiedsnapshot(AWSRegion,RDSInstance,subnetgroup)
    delete_snapshot(ACCESS_KEY,SECRET_KEY,SESSION_TOKEN,AWSRegion,RDSInstance)

    