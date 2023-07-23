import logging
import azure.functions as func
import pandas as pd
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import sys
import requests
import json
import base64
from datetime import datetime
import time

ORGANIZATION_NAME = "g*"
PROJECT_NAME = "A*"

# ADO
pat = "r*"

# blob
connect_str = "D*"

container_name = "strcontainertcsduration"

authorization = str(base64.b64encode(bytes(':'+pat, 'ascii')), 'ascii')

file_name = 'tcs_duration_3.csv'
cols_duration =  [
    # updates needed
    "App id", 
    "App name", 
    #"Feature id", 
    #"Feature", 
    #"User story id", 
    #"User story", 
    "Task id", 
    "Task",
    "Task description",
    "Start time",
    "End time",
    "Duration (min)"
]


def get_childs_list(app_id):
    #
    # Can be used to get all types of childs (user stories, features ...)
    #

    url = f"https://dev.azure.com/{ORGANIZATION_NAME}/{PROJECT_NAME}/_apis/wit/workitems/{app_id}/?$expand=all"
    # print(url)
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic '+ authorization,
    }
    response = requests.get(url, headers=headers)
    response_json = json.loads(response.text)

    user_story_work_items = response_json["relations"]

    child_ids = []
    for relation in user_story_work_items:
        if relation["rel"] == "System.LinkTypes.Hierarchy-Forward":
            url = relation["url"]
            parts = url.split('/')
            id = parts[-1]
            child_ids.append(id)
    childs_work_item_ids = child_ids
    return childs_work_item_ids





def get_duration(workitem_id):
    #
    # 
    #

    url = 'https://dev.azure.com/' + ORGANIZATION_NAME + '/' + PROJECT_NAME + '/_apis/wit/workItems/' + str(workitem_id) + '/updates?api-version=7.0'

    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic '+ authorization
    }
    response = requests.get(
        url = url,
        headers=headers,
    )
    changes = response.json()["value"]

    for state_change in reversed(changes):
        try:
            title = state_change["fields"]["Custom.PlaybookActivities"]['newValue']
            task_description = state_change["fields"]["Custom.PlaybookSubActivities"]['newValue']
            break
        except:
            title = None
            task_description = None


    app_history = response.json()["value"]

    status_change = None

    for state_change in reversed(app_history):
        try:
            if state_change["fields"]["System.State"]['oldValue'] == "Active" and state_change["fields"]["System.State"]['newValue'] == "Closed":
                status_change = state_change
                break
        except:
            val = 0

    # Calculate the duration of the work item in progress
    if status_change is not None:
        try:
            start_time = status_change["fields"]['Microsoft.VSTS.Common.StateChangeDate']['oldValue']
            end_time = status_change["fields"]['Microsoft.VSTS.Common.StateChangeDate']['newValue']

            in_progress_date = datetime.strptime(status_change["fields"]['Microsoft.VSTS.Common.StateChangeDate']['oldValue'], '%Y-%m-%dT%H:%M:%S.%fZ')
            closed_date = datetime.strptime(status_change["fields"]['Microsoft.VSTS.Common.StateChangeDate']['newValue'], '%Y-%m-%dT%H:%M:%S.%fZ')

            duration = closed_date - in_progress_date

            duration_sec = duration.seconds
            duration_min = duration_sec/60

        except:
            duration_min = None
            start_time = None
            end_time = None
    else:
        duration_min = None
        start_time = None
        end_time = None

    if duration_min is not None:
        duration_min = round(duration_min)

    #
    # If closed without in progress
    #

    for state_change in reversed(app_history):
        try:
            if state_change["fields"]["System.State"]['oldValue'] == "To Do" and state_change["fields"]["System.State"]['newValue'] == "Closed":
                status_change = state_change
                break
        except:
            val = 0

    # Calculate the duration of the work item in progress
    if status_change is not None:
        try:
            # start_time = status_change["fields"]['Microsoft.VSTS.Common.StateChangeDate']['oldValue']
            end_time = status_change["fields"]['Microsoft.VSTS.Common.StateChangeDate']['newValue']
            closed_date = datetime.strptime(status_change["fields"]['Microsoft.VSTS.Common.StateChangeDate']['newValue'], '%Y-%m-%dT%H:%M:%S.%fZ')
        except:
            duration_min = None
            start_time = None
            end_time = None
    # end of closed w/o in progress


    return (duration_min, title, task_description, start_time, end_time)





def get_app_title(workitem_id):
    #
    # 
    #
    url = 'https://dev.azure.com/' + ORGANIZATION_NAME + '/_apis/wit/workItems/' + str(workitem_id) + '?$expand=all'
    # print(url)
    # url = 'https://dev.azure.com/' + ORGANIZATION_NAME + '/' + PROJECT_NAME + '/_apis/wit/workItems/' + str(workitem_id) + '/updates?api-version=7.0'

    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic '+ authorization
    }
    response = requests.get(
        url = url,
        headers=headers,
    )

    try:
        title = response.json()["fields"]["System.Title"]
    except:
        title = None

    return title



def save_duration_to_df(app_id, df_duration):
    #
    #
    #
    app_title = get_app_title(app_id)

    task_ids = get_childs_list(app_id)

    for task_id in task_ids:
        # duration, task_title, start_time, end_time = get_duration(task_id)
        duration, task_title, task_description, start_time, end_time = get_duration(task_id)
        new_row = [app_id, app_title, task_id, task_title, task_description, start_time, end_time, duration]
        # new_row = [app_id, app_title, feature_id, feature_title, user_story_id, user_story_title, task_id, task_title, start_time, end_time, duration]
        new_df = pd.DataFrame([new_row], columns=cols_duration)
        df_duration = pd.concat([df_duration, new_df], ignore_index = True)

    return df_duration



def get_list_of_migrated_apps():
    #
    #
    #
    list_of_apps = []
    # url = 'https://dev.azure.com/' + ORGANIZATION_NAME + '/' + PROJECT_NAME + '/_apis/wit/workItems/' + str(workitem_id) + '/updates?api-version=7.0'


    # good query (not yet to start, changed during the last 7 days)
    url = "https://dev.azure.com/" + ORGANIZATION_NAME + "/" + PROJECT_NAME + "/_apis/wit/wiql/00571464-1724-47f6-9e0d-57d4a38a7758"

    # for tests
    url = "https://dev.azure.com/" + ORGANIZATION_NAME + "/" + PROJECT_NAME + "/_apis/wit/wiql/cf2b3520-cd93-433d-8c45-46ab4c4c9ada"
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic '+ authorization
    }
    response = requests.get(
        url = url,
        headers=headers,
    )
    apps_raw_data = response.json()["workItems"]
    for app in apps_raw_data:
        list_of_apps.append(app["id"])
    return list_of_apps


def main(req: func.HttpRequest) -> func.HttpResponse:
    start_time = time.time()/60 # sec
    logging.info('Python HTTP trigger function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        df_duration = pd.DataFrame([], columns = cols_duration)

        app_id = 248102
        df_duration = save_duration_to_df(app_id, df_duration)

        
        df_duration.to_csv(file_name, index=False)

        # Send the CSV file to Azure Blob Storage
        
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)

        container_client = blob_service_client.get_container_client(container_name)
        blob_name = file_name

        with open(file_name, "rb") as data:
            container_client.upload_blob(name=blob_name, data=data)

        container_client.close()
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )
