import boto3, time, botocore, json, logging
from urllib import response
from botocore.exceptions import ClientError


logger = logging.getLogger()
logger.setLevel(logging.INFO)
session = boto3.Session()
sts_client = boto3.client('sts')

def BucketPolicyCleanup(Region, DestinationBucket, ACCESS_KEY, SECRET_KEY, SESSION_TOKEN):
    s3 = boto3.client('s3',
        region_name=Region,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN)
    
    s3.delete_bucket_policy(Bucket=DestinationBucket)
    policy_file = s3.get_object(Bucket=DestinationBucket, Key='SourceBucket_policy.json')
    policy_contents = policy_file['Body'].read().decode('utf-8')
    s3.put_bucket_policy(Bucket=DestinationBucket, Policy=policy_contents)


def lambda_handler(event, context):
    DestinationBucketAccountID = event['DestinationBucketAccountID']
    SourceBucket = event['SourceBucket']
    DestinationBucket = event['DestinationBucket']
    LambdaRole = event['LambdaRole']
    Region = event['region']
    s3prefix = event['s3prefix']

    try:
        response  = sts_client.assume_role(
            RoleArn="arn:aws:iam::%s:role/S3Backup" % DestinationBucketAccountID,
            RoleSessionName="Customer_Backup")
        ACCESS_KEY = response['Credentials']['AccessKeyId']
        SECRET_KEY = response['Credentials']['SecretAccessKey']
        SESSION_TOKEN = response['Credentials']['SessionToken']
    
    except ClientError as e:
        logger.error("An error occurred while assuming role: %s", str(e))
        return
    s3 = boto3.client('s3',
                            region_name=Region,
                            aws_access_key_id=ACCESS_KEY,
                            aws_secret_access_key=SECRET_KEY,
                            aws_session_token=SESSION_TOKEN)
    #Backup the bucket policy
    try:
        policy_response = s3.get_bucket_policy(Bucket=DestinationBucket)
        policy = json.loads(policy_response['Policy'])
        s3.put_object(Bucket=DestinationBucket, Key='DestinationBucket_policy.json', Body=json.dumps(policy, indent=4))
        s3.delete_bucket_policy(Bucket=DestinationBucket)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
            logger.info("No bucket policy found for 'SourceBucket'.")
        else:
            logger.error("An error occurred while reverting the old bucket policy: %s", str(e))
            return
        
    NewSourceBucket_policy = {
        "Version": "2008-10-17",
        "Statement": [
            {
            "Sid": "DataSyncCreateS3LocationAndTaskAccess",
            "Effect": "Allow",
            "Principal": {
                "AWS": LambdaRole
            },
            "Action": [
                "s3:GetBucketLocation",
                "s3:ListBucket",
                "s3:ListBucketMultipartUploads",
                "s3:AbortMultipartUpload",
                "s3:DeleteObject",
                "s3:GetObject",
                "s3:ListMultipartUploadParts",
                "s3:PutObject",
                "s3:GetObjectTagging",
                "s3:PutObjectTagging"
            ],
            "Resource": [
                "arn:aws:s3:::%s" % DestinationBucket,
                "arn:aws:s3:::%s/*" % DestinationBucket
            ]
            },
            {
            "Sid": "DataSyncCreateS3Location",
            "Effect": "Allow",
            "Principal": {
                "AWS": LambdaRole
            },
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::%s" % DestinationBucket
            }
        ]
    }

    try:
        NewSourceBucket_policy = json.dumps(NewSourceBucket_policy)
        s3.put_bucket_policy(Bucket=DestinationBucket, Policy=NewSourceBucket_policy)
        time.sleep(10)
    except Exception as e:
        logger.error("An error occurred while creating bucket policy: %s", str(e))
        BucketPolicyCleanup(Region, DestinationBucket, ACCESS_KEY, SECRET_KEY, SESSION_TOKEN)
        raise e
    
    #Copy Files from SourceBucket to DestinationBucket
    try:
        source_s3= session.client('s3', region_name=Region)
        source_objects =[]
        destination_objects = []
        paginator = source_s3.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=SourceBucket, Prefix=s3prefix)
        for page in page_iterator:
            for obj in page['Contents']:
                source_objects.append(obj['Key'])
                
        paginator = source_s3.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=DestinationBucket, Prefix=s3prefix)
        for page in page_iterator:
            for obj in page['Contents']:
                destination_objects.append(obj['Key'])
        
        missing_objects = list(set(source_objects) - set(destination_objects))
        for object_key in missing_objects:
                source_s3.copy_object(ACL='bucket-owner-full-control',
                                      Bucket=DestinationBucket,
                                      CopySource={'Bucket': SourceBucket, 'Key': object_key },
                                      Key=object_key )
                logger.info(obj['Key'])
                logger.info("Successfully copied objects from %s to %s", SourceBucket, DestinationBucket)
        
    except Exception as e:
        logger.error("An error occurred while copying objects: %s", str(e))
        raise e
    

   