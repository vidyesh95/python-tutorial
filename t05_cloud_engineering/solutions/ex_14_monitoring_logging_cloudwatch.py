"""Exercise 14: structured logs, custom metrics, alarms and EMF.

`cw` is a boto3 "cloudwatch" client and `logs` a "logs" client (moto-backed in tests).

Tasks
1. build_log_line: one JSON log line.
2. put_count_metric: publish a custom Count metric.
3. create_error_alarm: alarm on a metric that notifies an SNS topic.
4. build_emf: an Embedded Metric Format log record.
5. ship_logs: write messages to a CloudWatch Logs stream.

Run: uv run pytest t05_cloud_engineering -k cloudwatch
"""

import json
import time
from datetime import UTC, datetime
from typing import Any

from botocore.exceptions import ClientError


def build_log_line(level: str, message: str, /, **fields: Any) -> str:
    """Return ONE line of JSON (json.dumps, no newlines) with keys:

    - "timestamp": current UTC time, ISO 8601 (datetime.now(UTC).isoformat())
    - "level": `level` upper-cased
    - "message": `message`
    - plus every extra keyword in `fields`.

    `level` and `message` are positional-only, so extra fields may reuse those names.
    The three reserved keys always win: an extra field named "level" must not override the
    real level. Values that are not JSON serializable are converted with str.
    """
    entry = {
        **fields,
        "timestamp": datetime.now(UTC).isoformat(),
        "level": level.upper(),
        "message": message,
    }
    return json.dumps(entry, default=str)


def put_count_metric(
    cw: Any, namespace: str, name: str, value: float, dimensions: dict[str, str]
) -> None:
    """Call put_metric_data with ONE MetricData item: MetricName=name, Value=value,
    Unit "Count", and Dimensions as [{"Name": k, "Value": v}, ...] sorted by name.
    """
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
    """Create (put_metric_alarm) an alarm that fires when the Sum of the metric over a
    60-second period is >= threshold for 1 evaluation period, notifies `topic_arn` via
    AlarmActions, and treats missing data as "notBreaching".
    """
    cw.put_metric_alarm(
        AlarmName=alarm_name,
        Namespace=namespace,
        MetricName=metric_name,
        Statistic="Sum",
        Period=60,
        EvaluationPeriods=1,
        Threshold=threshold,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        TreatMissingData="notBreaching",
        AlarmActions=[topic_arn],
    )


def build_emf(
    namespace: str, metric_name: str, value: float, unit: str, dimensions: dict[str, str]
) -> dict[str, Any]:
    """Return an Embedded Metric Format record (a dict):

    {"_aws": {"Timestamp": <epoch milliseconds int>,
              "CloudWatchMetrics": [{"Namespace": namespace,
                                     "Dimensions": [sorted list of dimension names],
                                     "Metrics": [{"Name": metric_name, "Unit": unit}]}]},
     <each dimension name>: <dimension value>,
     <metric_name>: value}
    """
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


def ship_logs(logs: Any, group: str, stream: str, messages: list[str]) -> int:
    """Write `messages` to log group `group`, stream `stream`; return how many were written.

    Create the group and the stream first, but tolerate "ResourceAlreadyExistsException"
    (so calling ship_logs twice works). Use put_log_events with millisecond timestamps
    (strictly increasing is fine: now_ms + index). If `messages` is empty return 0 and do
    not call put_log_events.
    """
    for create, kwargs in (
        (logs.create_log_group, {"logGroupName": group}),
        (logs.create_log_stream, {"logGroupName": group, "logStreamName": stream}),
    ):
        try:
            create(**kwargs)
        except ClientError as err:
            if err.response["Error"]["Code"] != "ResourceAlreadyExistsException":
                raise
    if not messages:
        return 0
    now = int(time.time() * 1000)
    events = [{"timestamp": now + i, "message": m} for i, m in enumerate(messages)]
    logs.put_log_events(logGroupName=group, logStreamName=stream, logEvents=events)
    return len(events)
