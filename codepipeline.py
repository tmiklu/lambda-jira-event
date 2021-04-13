import boto3
import collections
import datetime
import json
import logging
import os
import time
import urllib3


# set up logging
logger       = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger('boto3').setLevel(logging.ERROR)

client       = boto3.client('codebuild')
codepipeline = boto3.client('codepipeline')
ssm          = boto3.client('ssm')
http         = urllib3.PoolManager()
url          = 'https://jira.xxx.net/rest/api/2/issue/'
time_date    = datetime.datetime.now()
role_arn     = 'arn:aws:iam::028960685088:role/service-role/AWSCodePipelineServiceRole-us-east-1-'
base64       = os.environ['SECRET']
headers      = {'Content-Type': 'application/json', 'Authorization': 'Basic ' + base64 + ''}


#
##
### functions
##
#

def ci_comment(ci_url):
    '''Return comment id for appending phases during CI build'''
    data                    = {'body': 'build logs'}
    encoded_data            = json.dumps(data).encode('utf-8')
    req                     = http.request('POST', ci_url, body=encoded_data, headers=headers)
    ci_comment.comment_id   = json.loads(req.data.decode('utf-8'))['id']
    return ci_comment.comment_id

def missing_issue_links(build_release):
    data         = {'body': time_date.strftime("%H:%M:%S %d/%b/%Y") + ' *BUILD ERROR* (!) Missing components in *Issue Links*'}
    encoded_data = json.dumps(data).encode('utf-8')
    req          = http.request('POST', build_release, body=encoded_data, headers=headers)
    return 'comment: BUILD ERROR - MISSING ISSUE LINKS' 

def post_comment(build_release, duplicate, value=None):
  '''Send BUILD ERROR or BUILD STARTED comment'''
  if duplicate > 0:
    data         = {'body': time_date.strftime("%H:%M:%S %d/%b/%Y") + ' *BUILD ERROR* (!) Duplicate services are not allowed. Duplicates: ' + '*' + ', '.join(value) +'*'}
    encoded_data = json.dumps(data).encode('utf-8')
    req          = http.request('POST', build_release, body=encoded_data, headers=headers)
    return 'comment: BUILD ERROR - DUPLICATES'
    #json.loads(req.data.decode('utf-8'))
  else:
    data         = {'body': time_date.strftime("%H:%M:%S %d/%b/%Y") + ' *BUILD STARTED* (i)' }
    encoded_data = json.dumps(data).encode('utf-8')
    req          = http.request('POST', build_release, body=encoded_data, headers=headers)
    return 'comment: BUILD STARTED'
    #return json.loads(req.data.decode('utf-8'))
  return 'None'
    

def get_project(build_release, project_name):
    '''find all build project provided from argument'''
    start_args = {
        'names':project_name
    }

    response = client.batch_get_projects(**start_args)
    result   = [i for i in response['projectsNotFound']]
    if result:
        data         = {'body': time_date.strftime("%H:%M:%S %d/%b/%Y") + ' *Build project not exists in AWS codebuild* (!) ' + ', '.join([str(element) for element in result]) }
        encoded_data = json.dumps(data).encode('utf-8')
        req          = http.request('POST', build_release, body=encoded_data, headers=headers)
        raise RuntimeError('Project for build does not exists in codebuild')
        return result

    return 'Project exists'


def update_pipeline(components, environment, repo_type, branch, url_env, issue_id):
    response = codepipeline.update_pipeline(
        pipeline={
            'name': components + '-' + environment,
            'roleArn': role_arn + components + '-' + environment,
            'artifactStore': {
                'type': 'S3',
                'location': 's3-artifact-repo-test1'
            },
            'stages': [
                {
                    'name': 'Source',
                    'actions': [
                        {
                            'name': 'Source',
                            'actionTypeId': {
                                'category': 'Source',
                                'owner': 'AWS',
                                'provider': repo_type,
                                'version': '1'
                            },
                            'configuration': {
                                'RepositoryName': components,
                                'BranchName': branch
                            },
                            'outputArtifacts': [
                                {
                                    'name': 'source'
                                },
                            ],
    
                            'region': 'us-east-1',
                        },
                    ]
                },
                {
                    'name': 'Build',
                    'actions': [
                        {
                            'name': 'Build',
                            'actionTypeId': {
                                'category': 'Build',
                                'owner': 'AWS',
                                'provider': 'CodeBuild',
                                'version': '1'
                            },
                            'configuration': {
                                'ProjectName': components,
                                'EnvironmentVariables': '[\
                                    {\"name\":\"url\",\"value\":\"' + url_env + '\",\"type\":\"PLAINTEXT\"},\
                                    {\"name\":\"id\",\"value\":\"' + issue_id + '\",\"type\":\"PLAINTEXT\"}\
                                ]'
      
                            },
                            'inputArtifacts': [
                            {
                                'name': 'source'
                            },
                            ],
                            'outputArtifacts': [
                            {
                                'name': 'artifact'
                            },
                        ],
                        },
                    ]
                },
            ],
        }
    )
    return 'pipeline updated: ', response['ResponseMetadata']['HTTPStatusCode']

def start_pipeline(components, environment):
    response = codepipeline.start_pipeline_execution(
        name = components + '-' + environment
    )
    return 'pipeline started', response['ResponseMetadata']['HTTPStatusCode']

#
##
### main program
##
#

def lambda_handler(event, context):
    # TODO implement
    print(event['body'])
    if not event['headers'].get('User-Agent', '').startswith('Atlassian HttpClient'):
        raise RuntimeError('User-Agent is "%s", not "Atlassian HttpClient*"' %
                           event['headers'].get('User-Agent', ''))

    if event['httpMethod'] == 'GET':
        raise RuntimeError('httpMethod is "%s", not "POST"' %
                           event['httpMethod'])
    
    data = json.loads(event['body'])
    
    if ('changelog' not in data):
        raise RuntimeError('Webhook request body does not allow this action')
    
    build_release = data['issue']['self'] + '/' + 'comment' + '/'
    environment   = data['issue']['fields']['customfield_18212']['value']
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
                resp                = http.request('GET', url + issue_id + '/', headers=headers)
                custom_field        = json.loads(resp.data.decode('utf-8'))['fields']
                branch              = custom_field['customfield_18210']['value']
                components          = custom_field['components'][0]['name']
                repo_url            = custom_field['customfield_18209']
                repo_type           = custom_field['customfield_18211']['value']
                
                component_list.append(components)

        print(component_list)

        #
        ## 1st level, check if issue links contain issue links
        #
        if not component_list:
            print(missing_issue_links(build_release))
            raise RuntimeError('Missing Issue Links')
        
        #
        ## 2nd level, check if project exists in AWS codebuild
        #
        print(get_project(build_release, component_list))
            
    
    duplicate_microservice = [item for item, count in collections.Counter(component_list).items() if count > 1]
    duplicate              = len(duplicate_microservice)
    
    #
    ## 3th level, check if no duplicates
    #
    if duplicate > 0:
        print(post_comment(build_release, duplicate, duplicate_microservice))
        raise RuntimeError('duplicate is "%s", is great than 0' %
                           duplicate)

    if component_list:
        for issue_links in data['issue']['fields']['issuelinks']:
            if issue_links['type']['id'] == '10334' and issue_links['outwardIssue']['fields']['issuetype']['id'] == '10358':
                if ('outwardIssue' not in issue_links):
                    raise RuntimeError('Webhook request body is missing outwardIssue')
                issue_id            = issue_links['outwardIssue']['id']
                #resp                = http.request('GET', url + issue_id + '/', headers=auth)
                resp                = http.request('GET', url + issue_id + '/', headers=headers)
                custom_field        = json.loads(resp.data.decode('utf-8'))['fields']
                repo_url            = custom_field['customfield_18209']
                branch              = custom_field['customfield_18210']['value']
                repo_type           = custom_field['customfield_18211']['value']
                url_env             = url + issue_id + '/'
                comment             = url_env + 'comment'
                components          = custom_field['components'][0]['name']
                
                #
                ## create comment, for later update during CI build
                #print(ci_comment(comment))
                
                #
                ## start build print(start_build(components, branch, repo_type, repo_url, url_env, issue_id, ci_comment.comment_id))
                
                #
                ## 4th level, start pipeline
                #
                print(update_pipeline(components, environment, repo_type, branch, url_env, issue_id))
                print(start_pipeline(components, environment))

        print(post_comment(build_release, duplicate, duplicate_microservice))
