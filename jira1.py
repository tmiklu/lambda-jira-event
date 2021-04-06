import boto3
import collections
import datetime
import json
import logging
import urllib3


# set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger('boto3').setLevel(logging.ERROR)
logging.getLogger('botocore').setLevel(logging.ERROR)


# disable all warnings
# urllib3.disable_warnings()
client    = boto3.client('codebuild')
#session   = Session()
#client    = session.create_client('codebuild', config=Config(connect_timeout=20, read_timeout=60, retries={'max_attempts': 2}))
ssm       = boto3.client('ssm')
# if ssl certificate expire, please enable this code
# http   = urllib3.PoolManager(cert_reqs='CERT_NONE')
http      = urllib3.PoolManager()
url       = 'https://xx.xx.xx/rest/api/2/issue/'
#auth   = urllib3.make_headers(basic_auth='xx-xx-xx:xxx')
time_date = datetime.datetime.now()


#
##
### functions
##
#
def credentials():
  response = ssm.get_parameter(Name='jira-credentials-api', WithDecryption=False)
  return response['Parameter']['Value']


def post_comment(build_release, duplicate, value=None):
  if duplicate > 0:
    data         = {'body': time_date.strftime("%H:%M:%S %d/%b/%Y") + ' *BUILD ERROR* (!) Duplicate services are not allowed. Duplicates: ' + '*' + ', '.join(value) +'*'}
    encoded_data = json.dumps(data).encode('utf-8')
    req          = http.request('POST', build_release, body=encoded_data, headers={'Content-Type': 'application/json', 'Authorization': 'Basic <base64>'})
    return 'comment: BUILD ERROR'
    #json.loads(req.data.decode('utf-8'))
  else:
    data         = {'body': time_date.strftime("%H:%M:%S %d/%b/%Y") + ' *BUILD STARTED* (/)' }
    encoded_data = json.dumps(data).encode('utf-8')
    req          = http.request('POST', build_release, body=encoded_data, headers={'Content-Type': 'application/json', 'Authorization': 'Basic <base64>'})
    return 'comment: BUILD STARTED'
    #return json.loads(req.data.decode('utf-8'))
  return 'None'


def start_build(branch, repo_type, repo_url, url_env):
    start_args = {
        'projectName':'xx-xx-xx',
        'sourceVersion':branch,
        'sourceTypeOverride':repo_type,
        'sourceLocationOverride':repo_url,
        'environmentVariablesOverride':[
            {'name':'url', 'value':url_env},
            {'name':'component', 'value':'test1'}
        ]
    }
    response = client.start_build(**start_args)
    return response['build']['buildNumber']


def get_project(project_name):
    start_args = {
        'names': [project_name]
    }
    response = client.batch_get_projects(**start_args)
    return response['projects'][0]['name']


#
##
### main program
##
#

def lambda_handler(event, context):
    # TODO implement
    if not event['headers'].get('User-Agent', '').startswith('Atlassian HttpClient'):
        raise RuntimeError('User-Agent is "%s", not "Atlassian HttpClient*"' %
                           event['headers'].get('User-Agent', ''))
    
    #print(get_project())
    if event['httpMethod'] == 'GET':
         raise RuntimeError('httpMethod is "%s", not "POST"' %
                           event['httpMethod'])
    
    data = json.loads(event['body'])
    
    if ('changelog' not in data):
        raise RuntimeError('Webhook request body does not allow this action!')
    
    build_release = data['issue']['self'] + '/' + 'comment' + '/'
    status_field  = data['changelog']['items'][0]['field']
    from_id       = data['changelog']['items'][0]['from']
    to_id         = data['changelog']['items'][0]['to']
    
    logger.info('Received webhook notification for %s %s from: %s to: %s', build_release, status_field, from_id, to_id)
    
    component_list = []
    if status_field == 'status' and from_id == '12801' and to_id == '3':
        for issue_links in data['issue']['fields']['issuelinks']:
            if issue_links['type']['id'] == '10334' and issue_links['outwardIssue']['fields']['issuetype']['id'] == '10358':
                if ('outwardIssue' not in issue_links):
                    raise RuntimeError('Webhook request body is missing outwardIssue')
                
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
    
    duplicate_microservice = [item for item, count in collections.Counter(component_list).items() if count > 1]
    duplicate              = len(duplicate_microservice)
    
    if duplicate > 0:
            print(post_comment(build_release, duplicate, duplicate_microservice))
            raise RuntimeError('duplicate is "%s", is great than 0' %
                           duplicate)
    
    if component_list:
        
        project_name = 'gracenote-ingester-test'
        
        print(get_project(project_name))
        
        for issue_links in data['issue']['fields']['issuelinks']:
            if issue_links['type']['id'] == '10334' and issue_links['outwardIssue']['fields']['issuetype']['id'] == '10358':
                if ('outwardIssue' not in issue_links):
                    raise RuntimeError('Webhook request body is missing outwardIssue')
                
                issue_id            = issue_links['outwardIssue']['id']
                #resp                = http.request('GET', url + issue_id + '/', headers=auth)
                resp                = http.request('GET', url + issue_id + '/', headers={'Content-Type': 'application/json', 'Authorization': 'Basic <base64>'})
                custom_field        = json.loads(resp.data.decode('utf-8'))['fields']
                repo_url            = custom_field['customfield_18209']
                branch              = custom_field['customfield_18210']['value']
                repo_type           = custom_field['customfield_18211']['value']
                url_env             = url + issue_id + '/'
                
                
                print(start_build(branch, repo_type, repo_url, url_env))
        
        print(post_comment(build_release, duplicate, duplicate_microservice))
