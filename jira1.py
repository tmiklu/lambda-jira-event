import json
import boto3
from botocore.vendored import requests

client = boto3.client('codebuild')
ssm    = boto3.client('ssm')

def lambda_handler(event, context):
    # TODO implement
    
    if event['httpMethod'] == 'POST':
      event_body = event['body']
      main_event = json.loads(event_body)
      
      #print(main_event)
      
      changelog_exist = 'changelog' in main_event
      
      if changelog_exist:
        print(changelog_exist)
        
        fix_version     = main_event['issue']['fields']['fixVersions'][0]['name']
        status_field    = main_event['changelog']['items'][0]['field']
        from_id         = main_event['changelog']['items'][0]['from']
        to_id           = main_event['changelog']['items'][0]['to']
        
        if status_field == 'status' and from_id == '12801' and to_id == '3':
  
          for issue_links in main_event['issue']['fields']['issuelinks']:
            
            if issue_links['type']['id'] == '10334' and issue_links['outwardIssue']['fields']['issuetype']['id'] == '10358':
  
              print(issue_links)
      
      else:
        print('Changelog object does not exists.')
  
    else:
      return {
              'statusCode': 405
      }
