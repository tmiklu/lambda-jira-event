import ast
import boto3
import botocore
import collections
import datetime
import json
import logging
import os
import time
import re
import urllib3
from parameters import put_platform


# set up logging
logger       = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger('boto3').setLevel(logging.ERROR)

codecommit   = boto3.client('codecommit')
client       = boto3.client('codebuild')
iam          = boto3.client('iam')
codepipeline = boto3.client('codepipeline')
ssm          = boto3.client('ssm')
http         = urllib3.PoolManager()
url          = os.environ['JIRA']
time_date    = datetime.datetime.now()
role_arn     = os.environ['ROLE_ARN']
base64       = os.environ['SECRET']
headers      = {'Content-Type': 'application/json', 'Authorization': 'Basic ' + base64 + ''}


#
##
### functions
##
#

def pipeline_view(ci_url, create_pipeline_comment):
    '''Return comment id for appending phases during CI build'''
    data                       = {'body': '[pipeline|' + create_pipeline_comment + ']'}
    encoded_data               = json.dumps(data).encode('utf-8')
    req                        = http.request('POST', ci_url, body=encoded_data, headers=headers)
    pipeline_view.comment_id   = json.loads(req.data.decode('utf-8'))['id']
    return pipeline_view.comment_id


def missing_issue_links(build_release):
    '''Send notification to comment in build release issue'''
    data         = {'body': time_date.strftime("%H:%M:%S %d/%b/%Y") + ' *BUILD ERROR* (!) Missing components in *Issue Links*'}
    encoded_data = json.dumps(data).encode('utf-8')
    req          = http.request('POST', build_release, body=encoded_data, headers=headers)
    return 'comment: BUILD ERROR - MISSING ISSUE LINKS'


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
    

def get_platform(build_release, repository):
    try:
        response = codecommit.get_file(
            repositoryName=repository,
            commitSpecifier='refs/heads/cicd',
            filePath='config.file'
        )
        result      = response['fileContent'].decode("utf-8")
        environment = ast.literal_eval(result)['environment'].upper()
        platform    = ast.literal_eval(result)['compute_platform'].upper()
        if platform == 'FARGATE' or platform == 'LAMBDA':
            return platform
        else:
            err_platform = 'Error! Platform ' + platform + ' not supported'
            data         = {'body': '(!) ' + err_platform}
            encoded_data = json.dumps(data).encode('utf-8')
            req          = http.request('POST', build_release, body=encoded_data, headers=headers)
            raise RuntimeError(err_platform)
    except botocore.exceptions.ClientError as err:
        err_message  = str(err)
        data         = {'body': '(!) ' + err_message}
        encoded_data = json.dumps(data).encode('utf-8')
        req          = http.request('POST', build_release, body=encoded_data, headers=headers)
        raise RuntimeError(str(err))


def get_environment(build_release, repository):
    try:
        response = codecommit.get_file(
            repositoryName=repository,
            commitSpecifier='refs/heads/cicd',
            filePath='config.file'
        )
        result      = response['fileContent'].decode("utf-8")
        environment = ast.literal_eval(result)['environment'].lower()
        if environment == 'dev' or environment == 'test' or environment == 'stag' or environment == 'prod':
            return environment
        else:
            err_environment = 'Error! Environment ' + environment + ' not supported'
            data            = {'body': '(!) ' + err_environment}
            encoded_data    = json.dumps(data).encode('utf-8')
            req             = http.request('POST', build_release, body=encoded_data, headers=headers)
            raise RuntimeError(err_platform)
    except botocore.exceptions.ClientError as err:
        err_message  = str(err)
        data         = {'body': '(!) ' + err_message}
        encoded_data = json.dumps(data).encode('utf-8')
        req          = http.request('POST', build_release, body=encoded_data, headers=headers)
        raise RuntimeError(str(err))


def check_role(build_release, components, environment, role_arn):
    try:
        response = iam.get_role(
            RoleName=components + '-' + environment
        )
        return response['Role']['Arn']
    except botocore.exceptions.ClientError as err:
       err_message  = err.response['Error']['Message']
       data         = {'body': '(!) ' + err_message}
       encoded_data = json.dumps(data).encode('utf-8')
       req          = http.request('POST', build_release, body=encoded_data, headers=headers)
       raise RuntimeError(str(err))



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


def update_pipeline(components, environment, repo_type, branch, url_env, issue_id, comment_id, platform, build_release):
    time.sleep(0.1)
    print(role_arn + components + '-' + environment)
    try:
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
                                'runOrder': 1,
                                'configuration': {
                                    'RepositoryName': components,
                                    'BranchName': branch,
                                    'PollForSourceChanges': 'false'
                                },
                                'outputArtifacts': [
                                    {
                                        'name': 'source_output'
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
                                'runOrder': 2,
                                'configuration': {
                                    'ProjectName': components,
                                    'EnvironmentVariables': '[\
                                        {\"name\":\"url\",\"value\":\"' + url_env + '\",\"type\":\"PLAINTEXT\"},\
                                        {\"name\":\"id\",\"value\":\"' + issue_id + '\",\"type\":\"PLAINTEXT\"},\
                                        {\"name\":\"ci\",\"value\":\"' + comment_id + '\",\"type\":\"PLAINTEXT\"}\
                                    ]'
          
                                },
                                'inputArtifacts': [
                                    {
                                        'name': 'source_output'
                                    },
                                ],
                                'outputArtifacts': [
                                    {
                                        'name': 'build_output'
                                    },
                                ],
                                'region': 'us-east-1',
                            },
                        ]
                    },
                    {
                        'name': 'Deploy',
                        'actions': [
                            {
                                'name': 'Deploy',
                                'actionTypeId': {
                                    'category': 'Invoke',
                                    'owner': 'AWS',
                                    'provider': 'Lambda',
                                    'version': '1'
                                },
                                'runOrder': 3,
                                'configuration': {
                                    'FunctionName': 'vls-compute-platform'
                                },
                                'region': 'us-east-1'
                            }
                        ]
                    },
                ],
                'version': 1
            }
        )
        return 'pipeline updated: ', response['pipeline']['name'], response['ResponseMetadata']['HTTPStatusCode']
        
    except botocore.exceptions.ClientError as err:
        err_message  = str(err)
        data         = {'body': '(!) ' + err_message}
        encoded_data = json.dumps(data).encode('utf-8')
        req          = http.request('POST', build_release, body=encoded_data, headers=headers)
        raise RuntimeError(str(err))
    

def start_pipeline(components, environment):
    time.sleep(0.1)
    try:
        response = codepipeline.start_pipeline_execution(
            name = components + '-' + environment
        )   
    except botocore.exceptions.ClientError as error:
        error.response['Error']['Code']

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
    #environment   = data['issue']['fields']['customfield_18212']['value']
    status_field  = data['changelog']['items'][0]['field']
    from_id       = data['changelog']['items'][0]['from']
    to_id         = data['changelog']['items'][0]['to']
    
    #
    ## put parameter in parameter store, for compute platform
    #
    #put_platform(platform)
    
    #logger.info('Received webhook notification for %s %s from: %s to: %s', build_release, environment, status_field, from_id, to_id)
    
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
                
                #
                ## 6th check if role exists in aws, terraform creates role for codepipeline same as c vls-<name>-<env>
                #
                environment = get_environment(build_release, components)
        
                print(check_role(build_release, components, environment, role_arn))

        print(component_list)
        
        #if not custom_field['customfield_18219']['value']:
        #    raise RuntimeError('Container field was not set')
        
        
        #
        ## 1st level, check if issue links contain issue links
        #
        if len(component_list) == 0:
            print(missing_issue_links(build_release))
            raise RuntimeError('Missing Issue Links')
        
        #
        ## 2nd level, check if project exists in AWS codebuild
        #
        print(get_project(build_release, component_list))
            
    
    duplicate_microservice = [item for item, count in collections.Counter(component_list).items() if count > 1]
    duplicate              = len(duplicate_microservice)
    
    #
    ## 3th level, check if there are no duplicates
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
                
                
                if re.search('core', components):
                    code_deploy = 'vls-app'
                
                if re.search('lambda', components):
                    code_deploy = 'vls-lambda'
                
                print(code_deploy)
                
                #
                ## create comment, for later update during CI build
                #
                create_pipeline_comment = 'https://console.aws.amazon.com/codesuite/codepipeline/pipelines/' + components + '-' + environment + '/view?region=us-east-1'
                print(pipeline_view(comment, create_pipeline_comment))
                
                #
                ## 4th check if platform is set in config file
                #
                platform    = get_platform(build_release, components)
                
                #
                ## 5th check if environment is set in config file
                #
                environment = get_environment(build_release, components)
                
                
                #
                ## create comment, for later update during CI build
                #
                create_pipeline_comment = 'https://console.aws.amazon.com/codesuite/codepipeline/pipelines/' + components + '-' + environment + '/view?region=us-east-1'
                print(pipeline_view(comment, create_pipeline_comment))
                
                
                #
                ## 6th level, start pipeline
                #
                print(update_pipeline(components, environment, repo_type, branch, url_env, issue_id, pipeline_view.comment_id, platform, build_release))
                print(start_pipeline(components, environment))

        print(post_comment(build_release, duplicate, duplicate_microservice))
