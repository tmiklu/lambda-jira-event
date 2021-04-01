import json
import boto3
import urllib3
from collections import Counter

# disable all warnings
# urllib3.disable_warnings()

client = boto3.client('codebuild')
ssm    = boto3.client('ssm')

def parameter():
    response = ssm.get_parameter(
      Name='jira-credentials-api',
      WithDecryption=True
      
    )
    return response['Parameter']['Value']

#print(parameter())

# if ssl certificate expire, please enable this code
# http   = urllib3.PoolManager(cert_reqs='CERT_NONE')
http   = urllib3.PoolManager()
url    = 'https://xxx.xxx.xxx/rest/api/2/issue/'
#auth   = urllib3.make_headers(basic_auth='xxxx:xxxx')

def post_api(build_release, k):
  data         = {'body': 'Duplicate microservices is not allowed: ' + k}
  encoded_data = json.dumps(data).encode('utf-8')
  req          = http.request('POST', build_release, body=encoded_data, headers={'Content-Type': 'application/json', 'Authorization': 'Basic <base64>'})
  #json.loads(req.data.decode('utf-8'))


def lambda_handler(event, context):
    # TODO implement
    # print(event['body'])
        
    if event['httpMethod'] == 'POST':
      event_body = event['body']
      main_event = json.loads(event_body)
      changelog_exist = 'changelog' in main_event
      if changelog_exist:
        build_release = main_event['issue']['self'] + '/' + 'comment' + '/'
        fix_version   = main_event['issue']['fields']['fixVersions'][0]['name']
        status_field  = main_event['changelog']['items'][0]['field']
        from_id       = main_event['changelog']['items'][0]['from']
        to_id         = main_event['changelog']['items'][0]['to']
        
        if status_field == 'status' and from_id == '12801' and to_id == '3':
          component_list = []
          for issue_links in main_event['issue']['fields']['issuelinks']:
            if issue_links['type']['id'] == '10334' and issue_links['outwardIssue']['fields']['issuetype']['id'] == '10358':
              outwardIssue = 'outwardIssue' in issue_links
              if outwardIssue:
                issue_id            = issue_links['outwardIssue']['id']
                #resp                = http.request('GET', url + issue_id + '/', headers=auth)
                resp                = http.request('GET', url + issue_id + '/', headers={'Content-Type': 'application/json', 'Authorization': 'Basic <base64>'})
                custom_field        = json.loads(resp.data.decode('utf-8'))['fields']
                repo_url            = custom_field['customfield_18209']
                branch              = custom_field['customfield_18210']['value']
                repo_type           = custom_field['customfield_18211']['value']
                components          = custom_field['components'][0]['name']
                    
                component_list.append(components)
          
          print(component_list)
          for k, v in Counter(component_list).items():
            if v > 1:
              print('Sending comment.', build_release)
              post_api(build_release, k)

    else:
      return {
              'statusCode': 405
      }
