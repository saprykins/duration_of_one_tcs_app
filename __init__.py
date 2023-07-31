# 0/ access to calls
# in azure - allow calls from externals
# 2/ hide connections
# 3/ where do we specify environment 
# - during project creation
# - in vscode corner
# 4/ tbc W approach: no import 
# 5/ contact smn in D


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

# container_name = "strcontainertcsduration"

authorization = str(base64.b64encode(bytes(':'+pat, 'ascii')), 'ascii')

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
    # duration for tasks only
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
        new_df = pd.DataFrame([new_row], columns=cols_duration)
        df_duration = pd.concat([df_duration, new_df], ignore_index = True)

    return df_duration



def update_workitem_description(new_description, workitem_id):
    # 
    # to save to workitem data received after fnc terminated
    # can be link to bucket
    # 
    url = f"https://dev.azure.com/{ORGANIZATION_NAME}/{PROJECT_NAME}/_apis/wit/workitems/{workitem_id}?api-version=7.0"

    headers = {
        "Content-Type": "application/json-patch+json"
    }

    body = [
        {
            "op": "add",
            "path": "/fields/System.Description",
            "value": new_description
        },
        {
            "op": "add",
            "path": "/fields/System.State",
            "value": "Closed"
        }
    ]

    r = requests.patch(
        url,
        data=json.dumps(body),
        headers=headers,
        auth=("", pat),
    )
    print(r)



def create_attachment(filename, content):
    #
    # Upload CSV file content as an attachment
    #
    url = f"https://dev.azure.com/{ORGANIZATION_NAME}/{PROJECT_NAME}/_apis/wit/attachments?fileName={filename}&uploadType=simple&api-version=7.1-preview"

    headers = {
        "Content-Type": "application/octet-stream",
        "Authorization": f"Basic {authorization}"
    }

    r = requests.post(
        url,
        data=content,
        headers=headers
    )

    return r



def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        # Get the payload from the request body
        payload = req.get_json()

        # Extract the "Custom.app_id" field value as a float
        parent_id_float = payload['resource']['fields']['Custom.app_id'] # work item id, or where will upload data        
        parent_id_int = int(parent_id_float)
        parent_id_int = str(parent_id_int)

        # Get wi id (where description will be updated)
        wi_id_float = payload['resource']['id']
        wi_id_int = int(wi_id_float)

    except Exception as e:
        return func.HttpResponse(f"Error processing the webhook payload: {str(e)}", status_code=500)
    
    if parent_id_int:
        file_name = 'tcs_duration_app_id_' + parent_id_int + '.csv'
        df_duration = pd.DataFrame([], columns = cols_duration)
        df_duration = save_duration_to_df(parent_id_int, df_duration)
        df_duration.to_csv(file_name, index=False)
        
        # Read the CSV file content
        with open(file_name, "rb") as file:
            csv_content = file.read()

        # Upload CSV file content as an attachment
        attachment_response = create_attachment(file_name, csv_content)
        
        
        # Get the attachment URL from the "Location" header in the response
        attachment_url = attachment_response.json()["url"]


        # Attach the file to the work item
        url = f"https://dev.azure.com/{ORGANIZATION_NAME}/{PROJECT_NAME}/_apis/wit/workitems/{wi_id_int}?api-version=7.1-preview"
        
        
        headers = {
            "Content-Type": "application/json-patch+json",
            "Authorization": f"Basic {authorization}"
        }

        # Update the JSON payload with the correct attachment URL
        body = [
            {
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": "AttachedFile",
                    "url": attachment_url,
                    "attributes": {
                        "comment": "CSV file attachment"
                    }
                }
            }
        ]

        r = requests.patch(
            url,
            json=body,  # Use "json" parameter to send JSON payload
            headers=headers
        )

        print(r)



        '''
        # Send the CSV file to Azure Blob Storage
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)

        container_client = blob_service_client.get_container_client(container_name)
        blob_name = file_name

        with open(file_name, "rb") as data:
            container_client.upload_blob(name=blob_name, data=data, overwrite=True)
        
        # URL
        download_url = container_client.url
        
        container_client.close()
        '''
        new_description = "Check the attachment"
        update_workitem_description(new_description, wi_id_int)
        
        
        
        return func.HttpResponse(f"Duration for application_id {parent_id_int} was generated successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a 'application id' such as '248102' in the field app_id",
             status_code=200
        )
