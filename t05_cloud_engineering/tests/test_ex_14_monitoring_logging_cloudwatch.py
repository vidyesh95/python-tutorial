import json
from datetime import UTC, datetime, timedelta

import pytest

boto3 = pytest.importorskip("boto3")
from moto import mock_aws  # noqa: E402

from _loader import load  # noqa: E402

ex = load("t05_cloud_engineering", "ex_14_monitoring_logging_cloudwatch")


@pytest.fixture
def aws(monkeypatch):
    for key, value in {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "AWS_DEFAULT_REGION": "us-east-1",
    }.items():
        monkeypatch.setenv(key, value)
    with mock_aws():
        yield {
            name: boto3.client(name, region_name="us-east-1")
            for name in ("cloudwatch", "logs", "sns")
        }


def test_build_log_line_is_single_json_line():
    line = ex.build_log_line("info", "order created", order_id=7, tags=["a"])
    assert "\n" not in line
    data = json.loads(line)
    assert data["level"] == "INFO" and data["message"] == "order created"
    assert data["order_id"] == 7 and data["tags"] == ["a"]
    parsed = datetime.fromisoformat(data["timestamp"])
    assert abs(datetime.now(UTC) - parsed) < timedelta(seconds=5)


def test_reserved_keys_cannot_be_overridden_and_non_json_is_str():
    data = json.loads(ex.build_log_line("error", "boom", level="DEBUG", message="x", when=1 + 2j))
    assert data["level"] == "ERROR" and data["message"] == "boom"
    assert data["when"] == "(1+2j)"


def test_put_count_metric(aws):
    cw = aws["cloudwatch"]
    ex.put_count_metric(cw, "Taskboard", "Errors", 3, {"Service": "api", "Env": "prod"})
    metrics = cw.list_metrics(Namespace="Taskboard")["Metrics"]
    assert [m["MetricName"] for m in metrics] == ["Errors"]
    assert {d["Name"]: d["Value"] for d in metrics[0]["Dimensions"]} == {
        "Service": "api",
        "Env": "prod",
    }
    now = datetime.now(UTC)
    stats = cw.get_metric_statistics(
        Namespace="Taskboard",
        MetricName="Errors",
        Dimensions=metrics[0]["Dimensions"],
        StartTime=now - timedelta(minutes=10),
        EndTime=now + timedelta(minutes=10),
        Period=3600,
        Statistics=["Sum"],
        Unit="Count",
    )
    assert sum(p["Sum"] for p in stats["Datapoints"]) == 3


def test_create_error_alarm(aws):
    cw, sns = aws["cloudwatch"], aws["sns"]
    topic = sns.create_topic(Name="alerts")["TopicArn"]
    ex.create_error_alarm(cw, "api-errors", "Taskboard", "Errors", 5, topic)
    alarm = cw.describe_alarms(AlarmNames=["api-errors"])["MetricAlarms"][0]
    assert alarm["Namespace"] == "Taskboard" and alarm["MetricName"] == "Errors"
    assert alarm["Statistic"] == "Sum" and alarm["Period"] == 60
    assert alarm["EvaluationPeriods"] == 1 and alarm["Threshold"] == 5
    assert alarm["ComparisonOperator"] == "GreaterThanOrEqualToThreshold"
    assert alarm["AlarmActions"] == [topic]
    assert alarm["TreatMissingData"] == "notBreaching"


def test_build_emf():
    before = int(datetime.now(UTC).timestamp() * 1000)
    emf = ex.build_emf("Taskboard", "Latency", 42.5, "Milliseconds", {"Service": "api", "Env": "p"})
    assert emf["Latency"] == 42.5 and emf["Service"] == "api" and emf["Env"] == "p"
    meta = emf["_aws"]
    assert isinstance(meta["Timestamp"], int) and meta["Timestamp"] >= before - 1000
    directive = meta["CloudWatchMetrics"][0]
    assert directive["Namespace"] == "Taskboard"
    assert directive["Dimensions"] == [["Env", "Service"]]
    assert directive["Metrics"] == [{"Name": "Latency", "Unit": "Milliseconds"}]
    json.dumps(emf)  # must be serializable as a log line


def test_ship_logs_creates_and_is_repeatable(aws):
    logs = aws["logs"]
    assert ex.ship_logs(logs, "/app/api", "i-1", ["one", "two"]) == 2
    assert ex.ship_logs(logs, "/app/api", "i-1", ["three"]) == 1  # group/stream already exist
    events = logs.filter_log_events(logGroupName="/app/api")["events"]
    assert sorted(e["message"] for e in events) == ["one", "three", "two"]


def test_ship_logs_empty(aws):
    assert ex.ship_logs(aws["logs"], "/app/empty", "s", []) == 0
    groups = aws["logs"].describe_log_groups(logGroupNamePrefix="/app/empty")["logGroups"]
    assert len(groups) == 1
