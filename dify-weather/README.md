# Dify wether
Simple app to test dify upgrades:
1. Ussed as a Custom Tool for workflows and agents
2. It shows headers to check dify chat set them properly

## Usage
* Run it as Shakudo microservice
* Create Custom Tool providing openapi.json to Dify. Apart from it add the folowing section into openapi.json. In my cases I added it between "info" and "paths" sections
```
        "servers": [
        {
            "url": "https://your.domain.io"
        }
        ],
```

