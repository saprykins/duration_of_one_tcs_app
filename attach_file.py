import base64
import pandas as pd
import requests
import json


ORGANIZATION_NAME = "g*"
PROJECT_NAME = "A*"

# ADO
pat = "t*" # full tempo

# blob
connect_str = "D*"

container_name = "strcontainertcsduration"

organization = ORGANIZATION_NAME
project = PROJECT_NAME


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

data = [
    ["app_id_1", "app_name_1", "task_id_1", "task_name_1", "task_description_1", "start_time_1", "end_time_1", "duration_1"],
    ["app_id_2", "app_name_2", "task_id_2", "task_name_2", "task_description_2", "start_time_2", "end_time_2", "duration_2"],
    ["app_id_3", "app_name_3", "task_id_3", "task_name_3", "task_description_3", "start_time_3", "end_time_3", "duration_3"]
]

df_duration = pd.DataFrame(data, columns=cols_duration)

# Define the organization and project variables
organization = ORGANIZATION_NAME
project = PROJECT_NAME


def create_attachment(filename, content):
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


# Save DataFrame to a CSV file
csv_filename = "data.csv"
df_duration.to_csv(csv_filename, index=False)

# Read the CSV file content
with open(csv_filename, "rb") as file:
    csv_content = file.read()


# Upload CSV file content as an attachment
attachment_response = create_attachment(csv_filename, csv_content)

# Print the attachment response for debugging
# print("Attachment Response:", attachment_response.status_code, attachment_response.content)

# Get the attachment URL from the "Location" header in the response
attachment_url = attachment_response.json()["url"]

# Replace "your_workitem_id_here" with the actual ID of the work item where you want to attach the file
workitem_id = "291923"

# Attach the file to the work item
url = f"https://dev.azure.com/{ORGANIZATION_NAME}/{PROJECT_NAME}/_apis/wit/workitems/{workitem_id}?api-version=7.1-preview"

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
