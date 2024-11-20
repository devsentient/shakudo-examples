"""
Test file for the fastAPI application.
"""

import requests

url = "http://0.0.0.0:8000/"

# # Test the /recommendTables endpoint
# data = {
#     "prompt": "what are top 5 country in climate change metadata table?",
#     "schema": "climate",
# }
# response = requests.get(url + "recommendTables", params=data)
# print(response.json())


#  Test the /generateSQL endpoint
#  Pass data as JSON body
data = {
  "prompt": "what are the columns in temperature table?",
  "schema": "climate",
  "tables": "{\"data\": [\"climate_change_data_temperature\"]}"
}
response = requests.post(url + "generateSQL", json=data)
print(response.json())


# Test the /validateAndExecuteSQL endpoint
# Define the SQL code to validate and execute
# data = {"data": "SELECT COUNT(*) FROM climate.climate_change_data_metadata;"}
# response = requests.post(url + "validateAndExecuteSQL", json=data)
# print(response.json())
