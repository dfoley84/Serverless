from urllib import response
import boto3
from botocore.exceptions import ClientError

def delete_snapshot(ACCESS_KEY,SECRET_KEY,SESSION_TOKEN,AWSRegion,RDSInstance):
    print('Copying Snapshot', '\n')

    rds = boto3.client(
        'rds',
        region_name=AWSRegion,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN
    )
    Snapshots = [
        '%s-snapshot-shared' % RDSInstance,
        '%s-snapshot' % RDSInstance,
     ]
    try:
        for i in Snapshots:
            response = rds.delete_db_snapshot(
                DBSnapshotIdentifier=i
            )
            print('Deleting Snapshot', '\n')
            waiter = rds.get_waiter('db_snapshot_deleted')
            waiter.wait(
                DBSnapshotIdentifier=i,
                WaiterConfig={
                        'Delay': 60,
                        'MaxAttempts': 100
                    }
                )
            print('Snapshot %s Deleted' % i, '\n')
    except ClientError as e:
        print(e)