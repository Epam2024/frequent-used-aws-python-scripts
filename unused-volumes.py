import boto3

ec2_client = boto3.client('ec2')
sns_client = boto3.client('sns')
sns_arn = 'arn:aws:sns:us-east-1:054037100898:unused-volumes-alerts'

def lambda_handler(event, context):
    # Describe all volumes
    volumes = ec2_client.describe_volumes()
    volumes_to_delete = []

    for volume in volumes['Volumes']:
        # Check if the volume is attached to an instance
        if len(volume['Attachments']) > 0:
            volume_id = volume['VolumeId']
            instance_id = volume['Attachments'][0]['InstanceId']

            # Check if the volume has any snapshots
            snapshots = ec2_client.describe_snapshots(Filters=[{'Name': 'volume-id', 'Values': [volume_id]}])
            if len(snapshots['Snapshots']) == 0:
                volumes_to_delete.append((volume_id, instance_id))
                print(f"Volume {volume_id} attached to instance {instance_id} has no snapshots.")

    email_body = "Volumes and Instances to be deleted: \n"
    for volume_id, instance_id in volumes_to_delete:
        email_body += f"Volume: {volume_id}, Instance: {instance_id}\n"

    # Send Email
    sns_client.publish(
        TopicArn=sns_arn,
        Message=email_body,
        Subject='Volumes and Instances deleted due to no snapshots',
    )
    print(email_body)

    # Delete volumes and instances
    for volume_id, instance_id in volumes_to_delete:
        # Terminate the instance
        ec2_client.terminate_instances(InstanceIds=[instance_id])
        print(f"Terminated instance: {instance_id}")

        # Wait for the instance to be terminated
        waiter = ec2_client.get_waiter('instance_terminated')
        waiter.wait(InstanceIds=[instance_id])

        # Delete the volume
        ec2_client.delete_volume(VolumeId=volume_id)
        print(f"Deleted volume: {volume_id}")