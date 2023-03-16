import boto3
import time 

def lambda_handler(event, context):
    source_table_name = event['sourcetablename']
    target_table_name = event['targettablename']
    Region = event['Region']
    RoleArn = event['RoleArn']
    customer = event['customer']
    batch_size = 300
    
    
    Session = boto3.Session()

    sts_client = boto3.client('sts')
    assumed_role_object = sts_client.assume_role(
        RoleArn=RoleArn,
        RoleSessionName='AssumeRoleSession1')
    credentials = assumed_role_object['Credentials']

    dynamodbSource = boto3.resource('dynamodb', region_name=Region,
                                    aws_access_key_id=credentials['AccessKeyId'],
                                    aws_secret_access_key=credentials['SecretAccessKey'],
                                    aws_session_token=credentials['SessionToken'])
    
    dynamodbTarget = Session.resource('dynamodb', region_name=Region)
    
    source_table = dynamodbSource.Table(source_table_name)
    target_table = dynamodbTarget.Table(target_table_name)

    response = source_table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr('clientId').eq(customer)
    )
    items = response['Items']

    while 'LastEvaluatedKey' in response:
        response = source_table.scan(
            ExclusiveStartKey=response['LastEvaluatedKey'],
            FilterExpression=boto3.dynamodb.conditions.Attr('clientId').eq(customer)
            )
        items.extend(response['Items'])

    num_items = len(items)
    if num_items > 0:
        num_batches = (num_items + batch_size - 1) // batch_size
        start_idx = 0
        for i in range(num_batches):
            end_idx = min(start_idx + batch_size, num_items)
            batch_items = items[start_idx:end_idx]
            retry = 0
            while retry < 5:
                try:
                    with target_table.batch_writer() as batch:
                        for item in batch_items:
                            batch.put_item(Item=item)
                    break
                except boto3.exceptions.botocore.exceptions.ClientError as e:
                    if e.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                        retry += 1
                        delay = (2 ** retry) * 0.1
                        time.sleep(delay)
                    else:
                        raise e
            start_idx = end_idx
    else:
        print('No items to migrate')


