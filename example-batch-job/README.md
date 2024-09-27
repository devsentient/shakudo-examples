## Batch sending jobs using Python and GraphQL Mutations

- `example-job.py` writes a uuid string to a designated minio bucket.
- `send-batch.py` creates 1000 such jobs, each with a uuid name. The script first sends 100 jobs, waits one minute, and then queries graphql every 30 seconds to check the number of jobs pending or in progress. If that number is less than 100, it sends the appropriate number of jobs, to maintain 100 running at once. Until all jobs are sent.