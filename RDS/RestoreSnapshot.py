from urllib import response
import boto3
from botocore.exceptions import ClientError


def restorecopiedsnapshot(AWSRegion, RDSInstance,subnetgroup):
    session = boto3.Session()
    client = session.client('rds', region_name=AWSRegion)

    #Restore Snapshot
    response = client.restore_db_instance_from_db_snapshot(
        DBInstanceIdentifier='%s-uat-snapshot' % RDSInstance,
        DBSnapshotIdentifier='%s-uat-snapshot' % RDSInstance,
        DBInstanceClass='db.t3.micro',
        Port=3306,
        AvailabilityZone='%sa' % AWSRegion,
        DBSubnetGroupName='%s' % subnetgroup,
        MultiAZ=False,
        PubliclyAccessible=False,
        AutoMinorVersionUpgrade=False,
        LicenseModel='general-public-license'
    )
    #Waiter
    waiter = client.get_waiter('db_instance_available')
    waiter.wait(
        DBInstanceIdentifier='%s-uat-snapshot' % RDSInstance,
        WaiterConfig={
            'Delay': 60,
            'MaxAttempts': 100
        }
    )
    print('DB Instance Available', '\n')






