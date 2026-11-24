# Track 05: Cloud Engineering

Goal: go from "my API runs on my laptop" to "I can run it safely on AWS or GCP". By the end
you will use cloud SDKs (boto3, Google Cloud clients) with least-privilege IAM, model data and
events with DynamoDB and SQS/SNS, ship code as Lambda functions or containers, describe
infrastructure as code (CDK, Pulumi, Compose, Kubernetes manifests), deploy through CI/CD
without long-lived keys, manage secrets, and monitor what you run.

Prerequisites: `t01_fundamentals`, `t02_intermediate` and `t04_fastapi_backend` (the capstone
deploys the t04 API; its Dockerfile and compose files are used in m_09 and m_12). Python 3.15,
managed with `uv`.

## Setup

```bash
uv sync --group cloud
```

Every lesson, exercise, and test runs OFFLINE with no cloud account and no credentials:
- AWS code runs against `moto` (`mock_aws`), an in-memory fake of AWS, with fake credentials
  set only inside the test or demo.
- GCP code is written against an injected client and demoed with an in-memory fake; the real
  `storage.Client()` path runs only if you set `GOOGLE_CLOUD_PROJECT`.
- Kubernetes manifests are built and linted offline; real cluster calls run only if you set
  `KUBECONFIG`.
- CDK and Pulumi programs live in `iac/` as READ-ONLY examples (`aws-cdk-lib` and `pulumi`
  are intentionally not installed); the lessons teach the concepts and test pure-Python pieces.
- The example GitHub Actions workflow is `ci/ci.yml`; it is parsed as text, never executed.

### Practising on a real account (optional, but worth it)

Moto teaches the APIs; a real account teaches IAM, quotas, and billing. If you try one:

- Use the free tier on a NEW account, and create a budget alert (for example $5) and a billing
  alarm BEFORE creating anything else.
- Authenticate with `aws configure sso` (IAM Identity Center) and `gcloud auth
  application-default login`, never long-lived access keys or service-account key files.
- NEVER commit credentials, `.env` files, kubeconfigs, or Terraform/Pulumi state to git. Add
  them to `.gitignore` first.
- Tag everything (`owner`, `env`), work in one region, and clean up after each session
  (`cdk destroy`, `pulumi destroy`, `docker compose down -v`, delete the cluster). NAT gateways,
  load balancers, databases and idle clusters bill by the hour.

## Lessons

| #  | Lesson (`m_NN_*.py`)                       | You learn                                                                 | Status |
|----|--------------------------------------------|---------------------------------------------------------------------------|--------|
| 01 | `m_01_cloud_fundamentals_iam`              | regions/AZs, shared responsibility, IAM roles and policies, evaluation    | ✅ |
| 02 | `m_02_boto3_s3`                            | clients vs resources, sessions, paginators, presigned URLs, multipart     | ✅ |
| 03 | `m_03_dynamodb`                            | key design, query, GSI, conditional writes, single-table intro            | ✅ |
| 04 | `m_04_sqs_sns_eventing`                    | queues, visibility timeout, DLQ, SNS fan-out, idempotent consumers        | ✅ |
| 05 | `m_05_lambda_python`                       | handler signature, events, cold starts, packaging, local invocation       | ✅ |
| 06 | `m_06_google_cloud_sdk`                    | ADC auth, Cloud Storage client, Pub/Sub and Cloud Run overview           | ✅ |
| 07 | `m_07_iac_aws_cdk_python`                  | apps/stacks/constructs, synth/diff/deploy, naming, tags, policy checks    | ✅ |
| 08 | `m_08_iac_pulumi`                          | stacks, state, config and secrets, outputs, preview                       | ✅ |
| 09 | `m_09_docker_compose`                      | multi-service compose, healthchecks, env files, validation in Python      | ✅ |
| 10 | `m_10_kubernetes_python_client`            | Deployment/Service/ConfigMap, probes, resources, pods behind a guard      | ✅ |
| 11 | `m_11_ci_cd_github_actions`                | workflow anatomy, uv + ruff + pytest in CI, OIDC deploys                  | ✅ |
| 12 | `m_12_serverless_fastapi_mangum_cloud_run` | Mangum adapter, API Gateway v2 events, Cloud Run container contract       | ✅ |
| 13 | `m_13_secrets_management`                  | Secrets Manager, Parameter Store, caching, rotation, GCP Secret Manager   | ✅ |
| 14 | `m_14_monitoring_logging_cloudwatch`       | structured logs, custom metrics, alarms, EMF                              | ✅ |

Each lesson has a matching exercise `exercises/ex_NN_*.py` (stubs that raise
`NotImplementedError`), a reference implementation `solutions/ex_NN_*.py`, and tests in
`tests/test_ex_NN_*.py`. Supporting files: `iac/cdk_app.py`, `iac/pulumi_main.py` (real IaC
programs, not executed) and `ci/ci.yml` (example workflow).

## How to work

1. Run the lesson and read the code next to its output.
2. Open the exercise, read the docstrings (they include examples), implement the stubs. AWS
   functions receive the boto3 client as a parameter; the tests inject moto-backed clients.
3. Run the tests for that exercise until they pass.
4. Only then compare with the solution.

### Run a lesson

```bash
uv run python -m t05_cloud_engineering.m_02_boto3_s3
```

### Run the tests

```bash
uv run pytest t05_cloud_engineering                      # all exercises (fail until you implement them)
uv run pytest t05_cloud_engineering -k dynamodb          # one exercise by keyword
uv run pytest t05_cloud_engineering -x                   # stop at the first failure
SOLUTIONS=1 uv run pytest t05_cloud_engineering          # test the reference solutions instead
```

Before you start, failures are `NotImplementedError`. That is expected.

### Lint and format

```bash
uv run ruff check t05_cloud_engineering && uv run ruff format t05_cloud_engineering
```

## Progress checklist

- [ ] 01 Cloud fundamentals and IAM: lesson read, exercise passing
- [ ] 02 Object storage with boto3 and S3: lesson read, exercise passing
- [ ] 03 DynamoDB data modeling: lesson read, exercise passing
- [ ] 04 SQS, SNS and event-driven design: lesson read, exercise passing
- [ ] 05 AWS Lambda with Python: lesson read, exercise passing
- [ ] 06 Google Cloud SDK and Python clients: lesson read, exercise passing
- [ ] 07 Infrastructure as Code with AWS CDK: lesson read, exercise passing
- [ ] 08 Infrastructure as Code with Pulumi: lesson read, exercise passing
- [ ] 09 Local stacks with Docker Compose: lesson read, exercise passing
- [ ] 10 Kubernetes with the Python client: lesson read, exercise passing
- [ ] 11 CI/CD with GitHub Actions: lesson read, exercise passing
- [ ] 12 Serverless FastAPI: Mangum and Cloud Run: lesson read, exercise passing
- [ ] 13 Secrets management: lesson read, exercise passing
- [ ] 14 Monitoring and logging with CloudWatch: lesson read, exercise passing
- [ ] Capstone below finished, deployed, monitored, and torn down
- [ ] `uv run ruff check t05_cloud_engineering` is clean

## Capstone project: deploy the t04 API to the cloud

Take the `taskboard` API from the t04 capstone (or `t04_fastapi_backend/docker/` if you did not
build it) and run it in the cloud as a service you would be happy to operate. Put the work in
its own folder (for example `capstone_t05/`) so the lesson files stay untouched. Choose AWS
(ECS Fargate) or GCP (Cloud Run); the requirements map one-to-one.

### Requirements

1. **Container**: build the t04 multi-stage image (non-root, healthcheck), tag it with the git
   SHA, and push it to ECR (or Artifact Registry). Listen on `$PORT` if you use Cloud Run.
2. **Compute**: run it on ECS Fargate behind an Application Load Balancer (or on Cloud Run),
   with 2+ tasks/instances, `/healthz` and `/readyz` wired to the platform health checks, and
   CPU/memory limits. Roll out new images without downtime.
3. **Database**: Postgres on RDS (or Cloud SQL) in private subnets, encrypted, with automated
   backups; run Alembic migrations as a separate one-off task/job before each deploy.
   Redis on ElastiCache (or Memorystore) is a stretch goal.
4. **Secrets and config**: the database URL and JWT secret come from Secrets Manager (or
   Secret Manager), injected at runtime; plain config from SSM Parameter Store. Nothing secret in
   the image, the repo, the IaC state outputs, or the logs. The task role may read ONLY those
   secrets.
5. **Least-privilege IAM**: separate execution role and task role (or service account), no
   wildcards; verify the policies with the linting techniques from m_01 and m_07.
6. **Infrastructure as code**: everything above defined in CDK (Python) or Pulumi, with
   mandatory tags (`owner`, `env`, `cost-center`), per-environment config (`dev`, `prod`), and
   `cdk diff` / `pulumi preview` output reviewed before every apply.
7. **CI/CD**: a GitHub Actions pipeline that on every pull request runs `uv run ruff check .`
   and the tests, and on merge to `main` builds and scans the image, pushes it, runs migrations,
   and deploys. Authenticate to the cloud with OIDC (no static keys) and a role whose trust
   policy is limited to your repository and branch; use an environment with manual approval for
   production.
8. **Monitoring and alarms**: JSON logs with the request id in CloudWatch Logs (or Cloud Logging)
   with a retention period, a custom or EMF metric for a business event (for example tasks
   created), and alarms with an SNS (or notification channel) action on: 5xx rate, p99 latency,
   unhealthy hosts, and database CPU or connections. Add a dashboard of the golden signals.
9. **Eventing (optional)**: send a "task assigned" notification through SNS -> SQS with a DLQ
   and an idempotent consumer (Lambda or a worker), and alarm on DLQ depth.
10. **Teardown script**: `scripts/teardown.sh` (or `make destroy`) that destroys the stack,
    deletes images and log groups, and prints what could still cost money. Run it, then check
    the billing console the next day.

### Suggested layout

```
capstone_t05/
├── app/                      # the t04 taskboard source (or a copy of it)
├── Dockerfile
├── infra/
│   ├── app.py                # CDK app (or Pulumi __main__.py)
│   ├── network.py            # VPC, subnets, security groups
│   ├── data.py               # RDS, secrets, parameters
│   ├── service.py            # ECR, ECS/Fargate or Cloud Run, load balancer
│   └── monitoring.py         # log groups, metrics, alarms, dashboard
├── .github/workflows/
│   ├── ci.yml                # lint + test on pull requests
│   └── deploy.yml            # build, push, migrate, deploy on main (OIDC)
├── scripts/
│   ├── migrate.sh
│   └── teardown.sh
└── tests/
    ├── test_policies.py      # lint IAM policy JSON, assert no wildcards
    └── test_infra.py         # synthesized template: encryption, tags, no public buckets
```

Stretch: blue/green or canary deploys; autoscaling on request count; WAF in front of the load
balancer; the same service deployed to Kubernetes (m_10) as a comparison; cost report with
tags in Cost Explorer.
