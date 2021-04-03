import collections
import boto3
import json
import urllib3

# disable all warnings
# urllib3.disable_warnings()
client = boto3.client('codebuild')
ssm    = boto3.client('ssm')
# if ssl certificate expire, please enable this code
# http   = urllib3.PoolManager(cert_reqs='CERT_NONE')
http   = urllib3.PoolManager()
url    = 'https://jira.dtvlaops.net/rest/api/2/issue/'
#auth   = urllib3.make_headers(basic_auth='xxx:xxx')

#
##
### functions
##
#
def credentials():
  response = ssm.get_parameter(Name='jira-credentials-api', WithDecryption=True)
  return response['Parameter']['Value']


def post_comment(build_release, duplicate, value=None):
  if duplicate > 0:
    data         = {'body': 'BUILD ERROR: Duplicate services are not allowed. Duplicates: ' + ', '.join(value)}
    encoded_data = json.dumps(data).encode('utf-8')
    req          = http.request('POST', build_release, body=encoded_data, headers={'Content-Type': 'application/json', 'Authorization': 'Basic <base64>'})
    return 'comment: BUILD ERROR'
    #json.loads(req.data.decode('utf-8'))
  else:
    data         = {'body': 'BUILD STARTED' }
    encoded_data = json.dumps(data).encode('utf-8')
    req          = http.request('POST', build_release, body=encoded_data, headers={'Content-Type': 'application/json', 'Authorization': 'Basic <base64>'})
    return 'comment: BUILD STARTED'
    #return json.loads(req.data.decode('utf-8'))
  return 'None'


def start_build(branch, repo_type, repo_url, components, url_env):
  response = client.start_build(
    projectName            = 'gracenote-ingester-test',
    sourceVersion          = 'refs/heads/' + branch,
    sourceTypeOverride     = repo_type,
    sourceLocationOverride = repo_url,
                
    environmentVariablesOverride=[
     {
      'name': 'url',
      'value': url_env,
      'type': 'PLAINTEXT'
                  
     },
     {
      'name': 'num',
      'value': components,
      'type': 'PLAINTEXT'
                
     }
    ]
  )
  for i in response['build']['phases']:
    if i['phaseType'] == 'QUEUED':
      return i['phaseType']
      continue


#
##
### main program
##
#
def lambda_handler(event, context):
    # TODO implement
    # print(event['body'])

    if event['httpMethod'] == 'POST':
      event_body = event['body']
      main_event = json.loads(event_body)
      changelog_exist = 'changelog' in main_event
      
      if changelog_exist:
        build_release = main_event['issue']['self'] + '/' + 'comment' + '/'
        #fix_version   = main_event['issue']['fields']['fixVersions'][0]['name']
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
          
  # 
  ##
  ### find duplicate microservices
  ##
  #
          duplicate_microservice = [item for item, count in collections.Counter(component_list).items() if count > 1]
          duplicate              = len(duplicate_microservice)
  
  #
  ##
  ### build
  ##
  #
          if duplicate == 0:
            print('we are going to build component')
            print(post_comment(build_release, duplicate, duplicate_microservice))
          
            changelog_exist = 'changelog' in main_event
            if changelog_exist:
              build_release = main_event['issue']['self'] + '/' + 'comment' + '/'
              #fix_version   = main_event['issue']['fields']['fixVersions'][0]['name']
              status_field  = main_event['changelog']['items'][0]['field']
              from_id       = main_event['changelog']['items'][0]['from']
              to_id         = main_event['changelog']['items'][0]['to']
              
              if status_field == 'status' and from_id == '12801' and to_id == '3':
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
                      url_env             = url + issue_id + '/'
                      
                      #time.sleep(2)
                      print(branch, repo_type, repo_url, components, url_env)
                      build               = start_build(branch, repo_type, repo_url, components, url_env)
                      print(build)
                      
                      
                      #start_build(branch, repo_type, repo_url, components, issue_id)
                      
  
  #
  ##
  ### no build, duplicate exists
  ##
  #
          elif duplicate > 0:
            print(post_comment(build_release, duplicate, duplicate_microservice))

    else:
      return {
              'statusCode': 405
      }
