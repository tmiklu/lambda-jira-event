import json
import boto3
from botocore.vendored import requests

client = boto3.client('codebuild')
ssm    = boto3.client('ssm')


def lambda_handler(event, context):
    # TODO implement
    print(event['body'])
    if event['httpMethod'] == 'POST':
        
        json_event      = event['body']
        get_event       = json.loads(json_event)
        
        try:
          fix_version     = get_event['issue']['fields']['fixVersions'][0]['name']
          
          #repo_url        = get_event['issue']['fields']['customfield_18209']
          #source_type     = get_event['issue']['fields']['customfield_18211']['value']
          
          status_field    = get_event['changelog']['items'][0]['field']
          from_id         = get_event['changelog']['items'][0]['from']
          to_id           = get_event['changelog']['items'][0]['to']
          
        except:
          print('Exception occured. No build required')
        
        else:
          if status_field == 'status' and from_id == '12801' and to_id == '3':

            for issue_links in get_event['issue']['fields']['issuelinks']:
              
              try:
                issue_links['type']['id'] == '10334'
                issue_links['outwardIssue']['fields']['issuetype']['id'] == '10358'
                
                if issue_links['type']['id'] == '10334' and issue_links['outwardIssue']['fields']['issuetype']['id'] == '10358':
                  
                  print(issue_links['outwardIssue']['self'])
                  
                  username = ssm.get_parameter(
                      Name='jira-credentials-username',
                      WithDecryption=False
                  )
                  
                  password = ssm.get_parameter(
                      Name='jira-credentials-api',
                      WithDecryption=False
                  )
                  
                  url      = 'https://xxxx.xxx.xxx/rest/api/2/search?jql=fixversion=xx_xxx-x.x.x'
                  user     = username['Parameter']['Value']
                  passwd   = password['Parameter']['Value']
              
                  #x = requests.get(url, auth = (user, passwd))
                  #print(x.json())
              
              except:
                print('Exception occured. No build required')

        
    else:
      return {
              'statusCode': 405
        }
