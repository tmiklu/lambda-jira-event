import json
import boto3
import urllib3

client = boto3.client('codebuild')
ssm    = boto3.client('ssm')

              
def lambda_handler(event, context):
    # TODO implement
    #print(event['body'])
    if event['httpMethod'] == 'POST':
      event_body = event['body']
      main_event = json.loads(event_body)
      
      #print(main_event)
      
      changelog_exist = 'changelog' in main_event
      
      if changelog_exist:
        print(changelog_exist)
        
        fix_version  = main_event['issue']['fields']['fixVersions'][0]['name']
        status_field = main_event['changelog']['items'][0]['field']
        from_id      = main_event['changelog']['items'][0]['from']
        to_id        = main_event['changelog']['items'][0]['to']
        
        if status_field == 'status' and from_id == '12801' and to_id == '3':
          
          for issue_links in main_event['issue']['fields']['issuelinks']:
            
            if issue_links['type']['id'] == '10334' and issue_links['outwardIssue']['fields']['issuetype']['id'] == '10358':
  
              print(issue_links)
              
              issue_id = issue_links['outwardIssue']['id']
              
              username = ssm.get_parameter(
                Name           = 'jira-credentials-username',
                WithDecryption = False
                )
                                        
              password = ssm.get_parameter(
                Name           = 'jira-credentials-api',
                WithDecryption = True
                )
              
              
              http     = urllib3.PoolManager(cert_reqs='CERT_NONE')
              
              url      = 'https://jira.dtvlaops.net/rest/api/2/issue/' + issue_id + '/'
              user     = username['Parameter']['Value']
              passwd   = password['Parameter']['Value']
              
              
              authHeader = urllib3.make_headers(basic_auth=user + ':' + passwd)
              resp       =  http.request('GET', url, headers=authHeader)
              return json.loads(resp.data.decode('utf-8'))
      
      else:
        print('Changelog object does not exists. No build required.')
  
    else:
      return {
              'statusCode': 405
      }
