# # curl "http://0.0.0.0:8000/recommendTables?prompt=get+me+all+tables&schema=public"

# avenue_llama3_pov

import requests
url = "http://0.0.0.0:8000/recommendTables"

data = {
  "prompt": "what are top 5 country in climate change metadata table?",
  "schema": "climate",
}

response = requests.get(url, params=data)
print(response.json())


# import requests
# url = "http://0.0.0.0:8000/generateSQL"

# data = {
#   "prompt": "what are top 5 country in climate change metadata table?",
#   "schema": "climate",
#   "tables": ""
# }

# response = requests.get(url, params=data)
# print(response.json())

