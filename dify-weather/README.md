# Dify Weather
A simple app to test Dify upgrades:

* Used as a Custom Tool for workflows and agents
* Displays headers to verify that Dify Chat sets them correctly

## Usage
* Create a Custom Tool
* Run the server as a Shakudo microservice. Set the port to 8000.
* Create a Custom Tool by providing openapi.json to Dify. Additionally, include the following section in openapi.json. In my case, I added it between the "info" and "paths" sections:
```
"servers": [ { "url": "https://your.domain.io" } ],
```

### Agent
* Start creating an agent.
* Add the following instructions for the agent:
```
You are a weather expert.
Your task is to answer user questions related to the weather in London.
Assume that all user requests are about the weather in London.
Use external tools to provide users with the most accurate weather results.

A user might ask questions like:
"What is the weather right now in London?"
"What is the weather right now?"
"What is the weather like in London now?"
"What is the weather like now?"
```
* Attach the custom tool to the agent.
* Update the agent.
* Run the app.
* Ask a question like, "What is the weather right now in London?" The expected answer should be "The weather in London right now is 12°C," and the agent should indicate it used the tool "answer_question_api_answer_post".

### Workflow
* Create a simple workflow consisting of Start <-> answer_question_api_answer_post <-> End.
* answer_question_api_answer_post can be found in the Tools' custom section.
* Provide any random value as input to answer_question_api_answer_post.
* Run the workflow. answer_question_api_answer_post should output "The weather in London right now is 12°C."

## Example of openapi.json
```
{
   "openapi":"3.1.0",
   "info":{
      "title":"RAG Tutorial Backend Module",
      "version":"1.0.0"
   },
   "servers":[
      {
         "url":"http://hyperplane-service-0b65de.hyperplane-pipelines.svc.cluster.local:8787/api/answer"
      }
   ],
   "paths":{
      "/api/answer":{
         "post":{
            "summary":"Answer Question",
            "operationId":"answer_question_api_answer_post",
            "parameters":[
               {
                  "name":"input",
                  "in":"query",
                  "required":true,
                  "schema":{
                     "title":"Input"
                  }
               }
            ],
            "responses":{
               "200":{
                  "description":"Successful Response",
                  "content":{
                     "application/json":{
                        "schema":{
                           
                        }
                     }
                  }
               },
               "422":{
                  "description":"Validation Error",
                  "content":{
                     "application/json":{
                        "schema":{
                           "$ref":"#/components/schemas/HTTPValidationError"
                        }
                     }
                  }
               }
            }
         }
      }
   },
   "components":{
      "schemas":{
         "HTTPValidationError":{
            "properties":{
               "detail":{
                  "items":{
                     "$ref":"#/components/schemas/ValidationError"
                  },
                  "type":"array",
                  "title":"Detail"
               }
            },
            "type":"object",
            "title":"HTTPValidationError"
         },
         "ValidationError":{
            "properties":{
               "loc":{
                  "items":{
                     "anyOf":[
                        {
                           "type":"string"
                        },
                        {
                           "type":"integer"
                        }
                     ]
                  },
                  "type":"array",
                  "title":"Location"
               },
               "msg":{
                  "type":"string",
                  "title":"Message"
               },
               "type":{
                  "type":"string",
                  "title":"Error Type"
               }
            },
            "type":"object",
            "required":[
               "loc",
               "msg",
               "type"
            ],
            "title":"ValidationError"
         }
      }
   }
}
```