import json
import boto3
import urllib3
from collections import Counter

urllib3.disable_warnings()

client = boto3.client('codebuild')

http   = urllib3.PoolManager(cert_reqs='CERT_NONE')
url    = 'https://xx.xx.net/rest/api/2/issue/'
auth   = urllib3.make_headers(basic_auth='xxx:yyy')


def get_api(uid):
    resp                = http.request('GET', url + uid + '/', headers=auth)
    custom_field        = json.loads(resp.data.decode('utf-8'))['fields']
    get_api.repo_url    = custom_field['customfield_18209']
    get_api.branch      = custom_field['customfield_18210']['value']
    get_api.repo_type   = custom_field['customfield_18211']['value']
    get_api.components  = custom_field['components'][0]['name']


def lambda_handler(event, context):
    # TODO implement
    # print(event['body'])
        
    if event['httpMethod'] == 'POST':
      event_body = event['body']
      main_event = json.loads(event_body)
      
      #print(main_event)
      changelog_exist = 'changelog' in main_event
      
      if changelog_exist:
        fix_version  = main_event['issue']['fields']['fixVersions'][0]['name']
        status_field = main_event['changelog']['items'][0]['field']
        from_id      = main_event['changelog']['items'][0]['from']
        to_id        = main_event['changelog']['items'][0]['to']

        if status_field == 'status' and from_id == '12801' and to_id == '3':
          component_list = []
          for issue_links in main_event['issue']['fields']['issuelinks']:
            outwardIssue = 'outwardIssue' in issue_links
            if outwardIssue:
              issue_id  = issue_links['outwardIssue']['id']
                
              #get auth
              get_api(issue_id)
              #access var from func
              component = get_api.components
              component_list.append(component)
  
          for k, v in Counter(component_list).items():
            if v > 1:
              print('Error. Duplicate microservices:', k)
              quit()
          
          if status_field == 'status' and from_id == '12801' and to_id == '3':
            for issue_links in main_event['issue']['fields']['issuelinks']:
              if issue_links['type']['id'] == '10334' and issue_links['outwardIssue']['fields']['issuetype']['id'] == '10358':
                outwardIssue = 'outwardIssue' in issue_links
                if outwardIssue:
                  issue_id  = issue_links['outwardIssue']['id']
    
                  #get auth
                  get_api(issue_id)
                  
                  #access vars from func
                  branch    = get_api.branch
                  repo_type = get_api.repo_type
                  repo_url  = get_api.repo_url
                  ids       = url + issue_id
                  fix       = fix_version
                  component = get_api.components
                  
                  start_build(branch, repo_type, repo_url, ids, fix, component)
      
      else:
        print('Changelog object does not exists. No build required.')
        
    else:
      return {
              'statusCode': 405
      }


def start_build(a, b, c, d, e, f):
    print(a, b, c, d, e, f)
    response = client.start_build(
    
      projectName            = 'gracenote-ingester-test',
      sourceVersion          = 'refs/heads/' + a,
      sourceTypeOverride     = b,
      sourceLocationOverride = c,
            
      environmentVariablesOverride=[
       {
          'name': 'url',
          'value': d,
          'type': 'PLAINTEXT'
              
       },
       { 
          'name': 'num',
          'value': e,
          'type': 'PLAINTEXT'
              
       }
      ]
    )
