# This can be run as a job or in a session

import requests, json, time
import uuid 

graphql_endpoint = "http://api-server.hyperplane-core.svc.cluster.local:80/graphql"

def get_add_job_mutation():
    uuid_value = str(uuid.uuid4())[:18]
    add_job_mutation = f"""
    mutation {{
        createPipelineJobWithAlerting(
            input: {{
                jobName: "btest-{uuid_value}",
                jobType: "lite",
                pipelineYamlPath: "example-batch-job/run.sh",
                noHyperplaneCommands: false,
                workingDir: "/tmp/git/monorepo/",
                debuggable: false,
                notificationsEnabled: false,
                notificationTargetIds: [],
                timeout: 86400,
                activeTimeout: 86400,
                maxRetries: 1,
                gitServerName: "shakudo-examples",
                noGitInit: false,
                commitId: "",
                hyperplaneUserEmail: "yushuo@shakudo.io",
                serviceAccountName: "",
                pipelineType: "BASH",
                branchName: "example-batch-job",
                parameters: {{ create: [
                    {{ key: "FILE_ID", value: "{uuid_value}" }}
                ] }}
            }}
        ) {{
            id
            jobName
            jobType
            pipelineYamlPath
            workingDir
            commitId
            branchName
            debuggable
            parameters {{
                key
                value
            }}
        }}
    }}
    """
    return add_job_mutation

count_inprogress_query = """
query {
    COUNT_IN_PROGRESS_T_10M: getJobStat(
    stat: COUNT_IN_PROGRESS
    timeFrame: T_10M
  )
}
"""

count_pending_query = """
query {
    COUNT_PENDING_T_10M: getJobStat(stat: COUNT_PENDING, timeFrame: T_10M)
}
"""

def send_graphql_request(query):
    response = requests.post(
        graphql_endpoint,
        headers={"Content-Type": "application/json"},
        data=json.dumps({"query": query})
    )
    if response.status_code == 200:
        return response.json()
    else:
        print("Error:", response.status_code, response.text)
        return None

def main():
    total_jobs_to_send = 1000
    jobs_sent = 0

    # Send 100 jobs
    for _ in range(100):
        send_graphql_request(get_add_job_mutation())
        jobs_sent += 1
        print(f"Sent job {jobs_sent}/{total_jobs_to_send}")

    time.sleep(60)

    # Query the status every 30 seconds
    while jobs_sent < total_jobs_to_send:
        count_in_progress_response = send_graphql_request(count_inprogress_query)
        count_pending_response = send_graphql_request(count_pending_query)

        count_in_progress = count_in_progress_response.get("data", {}).get("COUNT_IN_PROGRESS_T_10M", 0) if count_in_progress_response else 0
        count_pending = count_pending_response.get("data", {}).get("COUNT_PENDING_T_10M", 0) if count_pending_response else 0

        total_jobs_in_progress_or_pending = count_in_progress + count_pending
        print(f"Jobs in progress: {count_in_progress}, Jobs pending: {count_pending}, Total: {total_jobs_in_progress_or_pending}")

        # If the total number of jobs in progress or pending is less than 100
        if total_jobs_in_progress_or_pending < 100:
            jobs_to_send = 100 - total_jobs_in_progress_or_pending
            for _ in range(jobs_to_send):
                send_graphql_request(get_add_job_mutation())
                jobs_sent += 1
                print(f"Sent job {jobs_sent}/{total_jobs_to_send}")

        # Wait for 30 seconds before the next query
        time.sleep(30)

if __name__ == "__main__":
    main()
