import boto3
import json
import time
Session = boto3.Session()

def backup(backupcommand,DropTable,CreateTable,RestoreTable,RemoveStateFile,instance_id):
    ssm = Session.client('ssm')
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': [backupcommand],
                    'executionTimeout': ['9200']
        },
        TimeoutSeconds=9200,
        Comment='Backup Database',
        CloudWatchOutputConfig = {
            'CloudWatchLogGroupName': 'RDSMigration',
            'CloudWatchOutputEnabled': True
        }
        )
    command_id = response['Command']['CommandId']
    time.sleep(10)
    output = ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id)
    
    while output['Status'] == 'InProgress':
        output = ssm.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id)
        time.sleep(5)

    if output['Status'] == 'Success':
        DropRDSTable(DropTable,CreateTable,RestoreTable,RemoveStateFile,instance_id)
    else:
        print('Backup Failed')
        exit(1)
    
def DropRDSTable(DropTable,CreateTable,RestoreTable,RemoveStateFile,instance_id):
    ssm = Session.client('ssm')
    DropTableRespone = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': [DropTable],
                    'executionTimeout': ['9200']},
        TimeoutSeconds=9200,
        Comment='Delete Database in Target RDS',
        CloudWatchOutputConfig = {
            'CloudWatchLogGroupName': 'RDSMigration',
            'CloudWatchOutputEnabled': True
        }
        )
    Dropcommand = DropTableRespone['Command']['CommandId']
    time.sleep(10)
    output1 = ssm.get_command_invocation(
        CommandId=Dropcommand,
        InstanceId=instance_id)
    while output1['Status'] == 'InProgress':
        output1 = ssm.get_command_invocation(
            CommandId=Dropcommand,
            InstanceId=instance_id)
        time.sleep(5)
    if output1['Status'] == 'Success':
        CreateRDSTable(CreateTable,RestoreTable,RemoveStateFile,instance_id)
    else:
        print('Drop Table Failed')
        exit(1)

def CreateRDSTable(CreateTable,RestoreTable,RemoveStateFile,instance_id):
    ssm = Session.client('ssm')
    CreateTableresponse = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': [CreateTable],
                    'executionTimeout': ['9200']},
        TimeoutSeconds=9200,
        Comment='Create Database in Target RDS',
        CloudWatchOutputConfig = {
            'CloudWatchLogGroupName': 'RDSMigration',
            'CloudWatchOutputEnabled': True
        }
    )
    Createcommand = CreateTableresponse['Command']['CommandId']
    time.sleep(10)

    output2 = ssm.get_command_invocation(
        CommandId=Createcommand,
        InstanceId=instance_id)
    
    while output2['Status'] == 'InProgress':
        output2 = ssm.get_command_invocation(
            CommandId=Createcommand,
            InstanceId=instance_id)
        time.sleep(5)
    if output2['Status'] == 'Success':
        RestoreRDSTable(RestoreTable,RemoveStateFile,instance_id)
    else:
        print('Create Table Failed')
        exit(1)


def RestoreRDSTable(RestoreTable,RemoveStateFile,instance_id):
    ssm = Session.client('ssm')
    RestoreTableresponse = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': [RestoreTable],
                    'executionTimeout': ['9200']},
        TimeoutSeconds=9200,
        Comment='Restore Database in Target RDS',
        CloudWatchOutputConfig = {
            'CloudWatchLogGroupName': 'RDSMigration',
            'CloudWatchOutputEnabled': True
        }
    )
    Restorecommand = RestoreTableresponse['Command']['CommandId']
    time.sleep(110)
    output3 = ssm.get_command_invocation(
        CommandId=Restorecommand,
        InstanceId=instance_id)
    print(output3)
    

def RemoveStateFile(RemoveStateFile,instance_id):
    ssm = Session.client('ssm')
    RemoveStateFileRespone = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': [RemoveStateFile],
                    'executionTimeout': ['9200']},
        TimeoutSeconds=7200,
        Comment='Remove State File'
        )
    RemoveStateFilecommand = RemoveStateFileRespone['Command']['CommandId']
    time.sleep(10)
    output1 = ssm.get_command_invocation(
        CommandId=RemoveStateFilecommand,
        InstanceId=instance_id)
    while output1['Status'] == 'InProgress':
        output1 = ssm.get_command_invocation(
            CommandId=RemoveStateFilecommand,
            InstanceId=instance_id)
        time.sleep(5)
    if output1['Status'] == 'Success':
        print('State File Removed')
    else:
        print('Failed to Remove State File')
        exit(1)


def lambda_handler(event, context):
    SourceRDS = event['SourceRDS']
    TargetRDS = event['TargetRDS']
    SourceUser = event['SourceUser']
    TargetUser = event['TargetUser']
    Sourcepwd = event['Sourcepwd']
    Targetpwd = event['Targetpwd']
    customer = event['customer']
    instance_id = event['instanceid']
    databaseTable = event['databaseTable']

    backupcommand = 'mysqldump --user="%s" --password="%s" -h %s %s > /tmp/%s.sql' % (SourceUser, Sourcepwd, SourceRDS,databaseTable,customer)
    DropTable = 'mysql --user="%s" --password="%s" -h %s -e "DROP DATABASE IF EXISTS %s"' % (TargetUser, Targetpwd, TargetRDS,databaseTable)
    CreateTable = 'mysql --user="%s" --password="%s" -h %s -e "CREATE DATABASE %s"' % (TargetUser, Targetpwd, TargetRDS,databaseTable)
    RestoreTable = 'mysql --user="%s" --password="%s" -h %s %s < /tmp/%s.sql' % (TargetUser, Targetpwd, TargetRDS,databaseTable,customer)
    RemoveStateFile = 'rm /tmp/%s.sql' % (customer)
    
    backup(backupcommand,DropTable,CreateTable,RestoreTable,RemoveStateFile,instance_id)

    
