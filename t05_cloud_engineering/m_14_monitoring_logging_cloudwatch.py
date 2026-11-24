# Monitoring and Logging with CloudWatch
"""
You cannot operate what you cannot see. CloudWatch is AWS's observability service; the three
signals are LOGS, METRICS and ALARMS (plus traces via X-Ray / OpenTelemetry, see t04 m_17).

Logs (CloudWatch Logs)
- Organized as LOG GROUPS (one per service, e.g. `/ecs/taskboard`) containing LOG STREAMS (one
  per container/instance). Lambda, ECS (awslogs driver) and Fargate ship stdout/stderr
  automatically; for other code call `put_log_events` or use an agent.
- Log STRUCTURED JSON, one object per line: `{"level": "ERROR", "message": ..., "request_id":
  ...}`. CloudWatch Logs Insights can then query fields:
      fields @timestamp, message | filter level = "ERROR" | stats count() by bin(5m)
- Set a RETENTION period on every group (default is "never expire" = growing bill).

Metrics (CloudWatch Metrics)
- A metric = NAMESPACE + NAME + DIMENSIONS (name/value labels like Service=api) + datapoints
  over time. AWS services publish their own (Lambda Errors, SQS queue depth, ALB 5XX).
- Custom metrics: `put_metric_data` (an API call per batch). Alternative with no API calls:
  EMBEDDED METRIC FORMAT (EMF): write a specially-shaped JSON log line with an `_aws` block;
  CloudWatch extracts the metrics from it asynchronously. Cheap and works from Lambda/ECS logs.
- DIMENSIONS multiply cost and cardinality: never use user ids or request ids as dimensions.
- Statistics: Sum, Average, Minimum, Maximum, SampleCount, percentiles (p95, p99) over a
  PERIOD (60 s and up; high resolution 1 s costs more).

Alarms
- An alarm watches ONE metric: "Sum of Errors >= 5 for 1 of 1 periods of 60 s" -> state
  OK / ALARM / INSUFFICIENT_DATA, and runs ACTIONS (publish to an SNS topic -> email, Slack,
  PagerDuty; or trigger auto scaling). Decide what `missing data` means (`notBreaching` for
  sparse error counts).
- Alert on SYMPTOMS users feel (error rate, latency p99, queue age, DLQ depth) rather than
  causes (CPU 70%). Every alarm should have a runbook.
- Dashboards group graphs per service; keep one "golden signals" dashboard per service:
  latency, traffic, errors, saturation.

Everything here runs on moto, no AWS account needed.

Common mistakes
- Unstructured, multi-line logs (stack traces split across events), or logging secrets/PII
  (m_13).
- No retention policy; logging at DEBUG in production; logging every request body.
- High-cardinality dimensions (user_id), or one custom metric per customer.
- Alarms that never fire (wrong period/missing-data) or fire constantly (alert fatigue).
- Alarming on averages: a few slow requests hide in the mean; use p95/p99 and error rate.
- Forgetting the alarm needs an action target and permission for SNS to be useful.

Production notes
- Put the request id (from your middleware, t04 m_13) in every log line to follow a request
  across services; add trace ids for distributed tracing.
- Use metric filters (turn a log pattern into a metric) for legacy logs, EMF for new code.
- Alarm on the DLQ (m_04), Lambda errors/throttles (m_05) and the ALB 5xx rate; add an
  anomaly-detection or composite alarm to cut noise.
- Export or subscribe logs to cheaper long-term storage (S3) if you need years of history.

Cost notes
- Logs: ingestion (~ $0.50/GB) is the big cost, then storage (~ $0.03/GB-month); Logs Insights
  bills per GB scanned. Log less, shorter, with retention.
- Metrics: ~ $0.30 per custom metric per month (each unique dimension combination counts);
  `put_metric_data` calls are billed too. Alarms ~ $0.10 each per month. First 10 custom
  metrics, 10 alarms and 5 GB logs a month are free.
"""

import json
import logging
import os
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch

import boto3
from botocore.exceptions import ClientError
from moto import mock_aws

FAKE_AWS_ENV = {
    "AWS_ACCESS_KEY_ID": "testing",
    "AWS_SECRET_ACCESS_KEY": "testing",
    "AWS_SESSION_TOKEN": "testing",
    "AWS_DEFAULT_REGION": "us-east-1",
}
RESERVED = ("timestamp", "level", "message")


# Example 1: structured JSON logs (one object per line)
def build_log_line(level: str, message: str, /, **fields: Any) -> str:
    entry = {
        **fields,
        "timestamp": datetime.now(UTC).isoformat(),
        "level": level.upper(),
        "message": message,
    }  # reserved keys come last so callers cannot overwrite them
    return json.dumps(entry, default=str)


class JsonFormatter(logging.Formatter):
    """Plug into the standard `logging` module so existing log calls become JSON."""

    def format(self, record: logging.LogRecord) -> str:
        extra = {k: v for k, v in getattr(record, "fields", {}).items() if k not in RESERVED}
        line = json.loads(build_log_line(record.levelname, record.getMessage(), **extra))
        if record.exc_info:
            line["exception"] = self.formatException(record.exc_info)  # stays ONE json line
        return json.dumps(line)


# Example 2: custom metric + alarm
def put_count_metric(
    cw: Any, namespace: str, name: str, value: float, dimensions: dict[str, str]
) -> None:
    cw.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                "MetricName": name,
                "Dimensions": [{"Name": k, "Value": v} for k, v in sorted(dimensions.items())],
                "Value": value,
                "Unit": "Count",
            }
        ],
    )


def create_error_alarm(
    cw: Any, alarm_name: str, namespace: str, metric_name: str, threshold: float, topic_arn: str
) -> None:
    cw.put_metric_alarm(
        AlarmName=alarm_name,
        Namespace=namespace,
        MetricName=metric_name,
        Statistic="Sum",
        Period=60,
        EvaluationPeriods=1,
        Threshold=threshold,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        TreatMissingData="notBreaching",  # no errors = no datapoints = healthy
        AlarmActions=[topic_arn],
    )


# Example 3: Embedded Metric Format: a log line that CloudWatch turns into a metric
def build_emf(
    namespace: str, metric_name: str, value: float, unit: str, dimensions: dict[str, str]
) -> dict[str, Any]:
    return {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": namespace,
                    "Dimensions": [sorted(dimensions)],
                    "Metrics": [{"Name": metric_name, "Unit": unit}],
                }
            ],
        },
        **dimensions,
        metric_name: value,
    }


# Example 4: ship log lines to CloudWatch Logs
def ship_logs(logs: Any, group: str, stream: str, messages: list[str]) -> int:
    for create, kwargs in (
        (logs.create_log_group, {"logGroupName": group}),
        (logs.create_log_stream, {"logGroupName": group, "logStreamName": stream}),
    ):
        try:
            create(**kwargs)
        except ClientError as err:
            if err.response["Error"]["Code"] != "ResourceAlreadyExistsException":
                raise
    now = int(time.time() * 1000)
    events = [{"timestamp": now + i, "message": m} for i, m in enumerate(messages)]
    logs.put_log_events(logGroupName=group, logStreamName=stream, logEvents=events)
    return len(events)


def run_demo() -> None:
    line = json.loads(build_log_line("info", "order created", order_id=7, level="HACKED"))
    print("log line:", {k: v for k, v in line.items() if k != "timestamp"})

    logger = logging.getLogger("demo")
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.handlers[:] = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.info("request done", extra={"fields": {"request_id": "abc", "status": 200}})

    cw = boto3.client("cloudwatch", region_name="us-east-1")
    sns = boto3.client("sns", region_name="us-east-1")
    for _ in range(3):
        put_count_metric(cw, "Taskboard", "Errors", 1, {"Service": "api"})
    now = datetime.now(UTC)
    stats = cw.get_metric_statistics(
        Namespace="Taskboard",
        MetricName="Errors",
        Dimensions=[{"Name": "Service", "Value": "api"}],
        StartTime=now - timedelta(minutes=5),
        EndTime=now + timedelta(minutes=5),
        Period=300,
        Statistics=["Sum"],
    )
    print("errors in window:", sum(p["Sum"] for p in stats["Datapoints"]))

    topic = sns.create_topic(Name="alerts")["TopicArn"]
    create_error_alarm(cw, "api-errors", "Taskboard", "Errors", 5, topic)
    alarm = cw.describe_alarms(AlarmNames=["api-errors"])["MetricAlarms"][0]
    print("alarm:", alarm["MetricName"], alarm["ComparisonOperator"], alarm["Threshold"])

    emf = build_emf("Taskboard", "Latency", 42.5, "Milliseconds", {"Service": "api"})
    print(
        "EMF namespace:",
        emf["_aws"]["CloudWatchMetrics"][0]["Namespace"],
        "| Latency:",
        emf["Latency"],
    )

    logs = boto3.client("logs", region_name="us-east-1")
    shipped = ship_logs(logs, "/taskboard/api", "i-1", [build_log_line("INFO", "boot")])
    events = logs.filter_log_events(logGroupName="/taskboard/api")["events"]
    print("shipped:", shipped, "| read back:", len(events))


if __name__ == "__main__":
    with patch.dict(os.environ, FAKE_AWS_ENV), mock_aws():
        run_demo()
