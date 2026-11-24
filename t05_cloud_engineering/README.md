# Track 05 — Cloud Engineering

**Who it's for:** Platform, cloud, and DevOps-leaning engineers who ship Python services to AWS or GCP

## Goals

- Use cloud SDKs (boto3, Google Cloud clients) safely with least-privilege IAM
- Define infrastructure as code with CDK or Pulumi and run local stacks with Compose
- Deploy, secure, and monitor services through CI/CD

## Prerequisite tracks

- t01_fundamentals, t02_intermediate, t04_fastapi_backend

## Setup

```bash
uv sync --group cloud
```

Note: Deployment lessons need an AWS or GCP account. Never commit credentials; prefer SSO, OIDC, or short-lived tokens.

## Lessons

| File | Topic | Status |
|---|---|---|
| `m_01_cloud_fundamentals_iam.py` | Cloud Fundamentals and IAM | STUB |
| `m_02_boto3_s3.py` | Object Storage with boto3 and S3 | STUB |
| `m_03_dynamodb.py` | DynamoDB Data Modeling | STUB |
| `m_04_sqs_sns_eventing.py` | SQS, SNS and Event-Driven Design | STUB |
| `m_05_lambda_python.py` | AWS Lambda with Python | STUB |
| `m_06_google_cloud_sdk.py` | Google Cloud SDK and Python Clients | STUB |
| `m_07_iac_aws_cdk_python.py` | Infrastructure as Code with AWS CDK (Python) | STUB |
| `m_08_iac_pulumi.py` | Infrastructure as Code with Pulumi | STUB |
| `m_09_docker_compose.py` | Local Multi-Service Stacks with Docker Compose | STUB |
| `m_10_kubernetes_python_client.py` | Kubernetes with the Python Client | STUB |
| `m_11_ci_cd_github_actions.py` | CI/CD with GitHub Actions | STUB |
| `m_12_serverless_fastapi_mangum_cloud_run.py` | Serverless FastAPI: Mangum and Cloud Run | STUB |
| `m_13_secrets_management.py` | Secrets Management | STUB |
| `m_14_monitoring_logging_cloudwatch.py` | Monitoring and Logging with CloudWatch | STUB |

## Checklist

- [ ] m_01: Cloud Fundamentals and IAM
- [ ] m_02: Object Storage with boto3 and S3
- [ ] m_03: DynamoDB Data Modeling
- [ ] m_04: SQS, SNS and Event-Driven Design
- [ ] m_05: AWS Lambda with Python
- [ ] m_06: Google Cloud SDK and Python Clients
- [ ] m_07: Infrastructure as Code with AWS CDK (Python)
- [ ] m_08: Infrastructure as Code with Pulumi
- [ ] m_09: Local Multi-Service Stacks with Docker Compose
- [ ] m_10: Kubernetes with the Python Client
- [ ] m_11: CI/CD with GitHub Actions
- [ ] m_12: Serverless FastAPI: Mangum and Cloud Run
- [ ] m_13: Secrets Management
- [ ] m_14: Monitoring and Logging with CloudWatch

## Capstone project

Deploy the t04 task-management API to AWS (or GCP). Requirements: the app is packaged as a container image and pushed to ECR (or Artifact Registry); infrastructure is defined in AWS CDK (Python) or Pulumi; Postgres runs on RDS (or Cloud SQL) and Redis on ElastiCache (or Memorystore); secrets come from Secrets Manager (or Secret Manager); GitHub Actions deploys on merge to main using OIDC instead of static keys; and logs plus an error-rate alarm go to CloudWatch (or Cloud Logging).
