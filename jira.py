import json
import boto3

client = boto3.client('codebuild')

def lambda_handler(event, context):
    # TODO implement
    print(event['body'])
    if event['httpMethod'] == 'POST':
        
        json_event      = event['body']
        get_event       = json.loads(json_event)
        
        #fixVersions
        fix_version     = get_event['issue']['fields']['fixVersions'][0]['name']
    
        #changelog
        status_field    = get_event['changelog']['items'][0]['field']
        from_id         = get_event['changelog']['items'][0]['from']
        to_id           = get_event['changelog']['items'][0]['to']
        
        # custom fields
        repo_url        = get_event['issue']['fields']['customfield_18209']
        source_type     = get_event['issue']['fields']['customfield_18211']['value']
        #print(source_type)
        
        # get bug == service-release
        #bug             = get_event['issue']['fields']['issuelinks']

        if status_field == 'status' and from_id == '12801' and to_id == '3':
            
            print('build started')
            response = client.start_build(
              projectName            = 'gracenote_ingester-build',
              sourceVersion          = 'refs/heads/cicd',
              sourceTypeOverride     = source_type,
              sourceLocationOverride = repo_url,
              
              environmentVariablesOverride=[
                {
                    'name': 'release_num',
                    'value': fix_version,
                    'type': 'PLAINTEXT'
                }
              ]
            )
              
        else:
            print('no build required')
            
    else:
        return {
                'statusCode': 405,
            }
    
