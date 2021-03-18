import json
import boto3

client = boto3.client('codebuild')

def lambda_handler(event, context):
    # TODO implement
    print(event)
	
if event['httpMethod'] == 'POST':
        
        get_event = event['body']
        
        get_release = json.loads(get_event)
    
        release = str(get_release['version']['name'])
    
        get_release_number = release.split('-')
    
        #print(get_release_number[1])
        
        print('Starting a new build ...')
        response = client.start_build(
          projectName   = 'vls-build',
          sourceVersion = 'refs/heads/develop',
          environmentVariablesOverride=[
            {
                'name': 'release_num',
                'value': get_release_number[1],
                'type': 'PLAINTEXT'
            }
          ]
        )
        
        # get project id
        get_project_id = json.loads(get_event)
        project_id = str(get_project_id['version']['projectId'])
        print(project_id)
        
        return {
                'statusCode': 200,
                'body': 'Status 200 - OK'
            }
    
    elif event['httpMethod'] == 'GET':
        
        return {
                'statusCode': 200,
                'body': 'Only POST method start codebuild'
            }
