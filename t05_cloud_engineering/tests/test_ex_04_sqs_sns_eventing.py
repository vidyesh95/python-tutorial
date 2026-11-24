import json

import pytest

boto3 = pytest.importorskip("boto3")
from moto import mock_aws  # noqa: E402

from _loader import load  # noqa: E402

ex = load("t05_cloud_engineering", "ex_04_sqs_sns_eventing")


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
            "sqs": boto3.client("sqs", region_name="us-east-1"),
            "sns": boto3.client("sns", region_name="us-east-1"),
        }


def test_create_queue_with_dlq_sets_redrive(aws):
    sqs = aws["sqs"]
    url, dlq_url = ex.create_queue_with_dlq(sqs, "jobs", max_receive=2)
    attrs = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["All"])["Attributes"]
    redrive = json.loads(attrs["RedrivePolicy"])
    dlq_arn = sqs.get_queue_attributes(QueueUrl=dlq_url, AttributeNames=["QueueArn"])["Attributes"][
        "QueueArn"
    ]
    assert redrive["deadLetterTargetArn"] == dlq_arn
    assert int(redrive["maxReceiveCount"]) == 2
    assert attrs["VisibilityTimeout"] == "30"


def test_poison_message_moves_to_dlq(aws):
    sqs = aws["sqs"]
    url, dlq_url = ex.create_queue_with_dlq(sqs, "jobs", max_receive=2)
    sqs.send_message(QueueUrl=url, MessageBody="poison")
    for _ in range(3):
        sqs.receive_message(QueueUrl=url, VisibilityTimeout=0)
    msgs = sqs.receive_message(QueueUrl=dlq_url).get("Messages", [])
    assert [m["Body"] for m in msgs] == ["poison"]


def test_fan_out_delivers_to_every_queue(aws):
    sqs, sns = aws["sqs"], aws["sns"]
    topic_arn, urls = ex.fan_out(sns, sqs, "events", ["billing", "shipping"])
    assert set(urls) == {"billing", "shipping"}
    assert topic_arn.endswith(":events")
    sns.publish(TopicArn=topic_arn, Message="hello")
    for url in urls.values():
        msgs = sqs.receive_message(QueueUrl=url).get("Messages", [])
        assert len(msgs) == 1
        assert ex.unwrap_sns_message(msgs[0]["Body"]) == "hello"


def test_unwrap_sns_message_passthrough():
    assert ex.unwrap_sns_message('{"Message": "x", "Type": "Notification"}') == "x"
    assert ex.unwrap_sns_message("plain text") == "plain text"
    assert ex.unwrap_sns_message('{"order": 1}') == '{"order": 1}'
    assert ex.unwrap_sns_message("[1, 2]") == "[1, 2]"


def test_drain_queue_processes_all_and_deletes(aws):
    sqs = aws["sqs"]
    url = sqs.create_queue(QueueName="work")["QueueUrl"]
    for i in range(12):
        sqs.send_message(QueueUrl=url, MessageBody=f"m{i}")
    seen: list[str] = []
    assert ex.drain_queue(sqs, url, seen.append) == 12
    assert sorted(seen) == sorted(f"m{i}" for i in range(12))
    attrs = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["ApproximateNumberOfMessages"])
    assert attrs["Attributes"]["ApproximateNumberOfMessages"] == "0"


def test_drain_queue_keeps_failed_messages(aws):
    sqs = aws["sqs"]
    url = sqs.create_queue(QueueName="work", Attributes={"VisibilityTimeout": "30"})["QueueUrl"]
    sqs.send_message(QueueUrl=url, MessageBody="good")
    sqs.send_message(QueueUrl=url, MessageBody="bad")

    def handler(body: str) -> None:
        if body == "bad":
            raise RuntimeError("boom")

    assert ex.drain_queue(sqs, url, handler) == 1
    attrs = sqs.get_queue_attributes(
        QueueUrl=url, AttributeNames=["ApproximateNumberOfMessagesNotVisible"]
    )["Attributes"]
    assert attrs["ApproximateNumberOfMessagesNotVisible"] == "1"  # still there, in flight


def test_process_once():
    seen: set[str] = set()
    calls: list[int] = []
    assert ex.process_once(seen, "a", lambda: calls.append(1)) is True
    assert ex.process_once(seen, "a", lambda: calls.append(2)) is False
    assert calls == [1]

    def boom() -> None:
        raise ValueError("fail")

    with pytest.raises(ValueError):
        ex.process_once(seen, "b", boom)
    assert "b" not in seen
    assert ex.process_once(seen, "b", lambda: calls.append(3)) is True
