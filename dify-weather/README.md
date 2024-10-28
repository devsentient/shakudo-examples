# Dify wether
Simple app to test dify upgrades:
1. Ussed as a Custom Tool for workflows and agents
2. It shows headers to check dify chat set them properly

## Usage
### Create a custom tool
* Run server as Shakudo microservice. Do not forget to set port to `8000`
* Create Custom Tool providing openapi.json to Dify. Apart from it add the folowing section into openapi.json. In my cases I added it between "info" and "paths" sections
```
        "servers": [
        {
            "url": "https://your.domain.io"
        }
        ],
```

### Agent
* Start creating agent
* Add the following instructions for the agent
```
You are wether expert
Your task is to answer user questions related wether in London
You can assume that all user requests about weather in London
You should use external tools to provide a user with the most accurate weather results.

A user might ask you the following questions:
"What is the weather right now in London?"
"What is the weather right now?"
"What is the weather like in London now?"
"What is the weather like now?"
```
* Attach the custom tool to the agent
* Update agent
* Run app
* Ask a question like "What is the weather right now in London?" the answer must be "The weather in London right now is 12°C." and agent shows it has used a tool "Used answer_question_api_answer_post"

### Workflow
* Create a simple workflow consisting of Start <-> answer_question_api_answer_post <-> End
* answer_question_api_answer_post can be found in the Tools custom section
* Give random value as input to the answer_question_api_answer_post
* run the workflow. answer_question_api_answer_post must output "The weather in London right now is 12°C."


## Example of openapi.json
```
{
    "openapi": "3.1.0",
    "info": {
      "title": "RAG Tutorial Backend Module",
      "version": "1.0.0"
    },
    "servers": [
        {
          "url": "http://hyperplane-service-191536.hyperplane-pipelines.svc.cluster.local:8787/api/answer"
        }
      ],
    "paths": {
      "/api/answer": {
        "post": {
          "summary": "Answer Question",
          "operationId": "answer_question_api_answer_post",
          "parameters": [
            {
              "name": "input",
              "in": "query",
              "required": true,
              "schema": {
                "title": "Input"
              }
            }
          ],
          "responses": {
            "200": {
              "description": "Successful Response",
              "content": {
                "application/json": {
                  "schema": {
  
                  }
                }
              }
            },
            "422": {
              "description": "Validation Error",
              "content": {
                "application/json": {
                  "schema": {
                    "$ref": "#/components/schemas/HTTPValidationError"
                  }
                }
              }
            }
          }
        }
      }
    },
    "components": {
      "schemas": {
        "HTTPValidationError": {
          "properties": {
            "detail": {
              "items": {
                "$ref": "#/components/schemas/ValidationError"
              },
              "type": "array",
              "title": "Detail"
            }
          },
          "type": "object",
          "title": "HTTPValidationError"
        },
        "ValidationError": {
          "properties": {
            "loc": {
              "items": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "integer"
                  }
                ]
              },
              "type": "array",
              "title": "Location"
            },
            "msg": {
              "type": "string",
              "title": "Message"
            },
            "type": {
              "type": "string",
              "title": "Error Type"
            }
          },
          "type": "object",
          "required": [
            "loc",
            "msg",
            "type"
          ],
          "title": "ValidationError"
        }
      }
    }
  }
```