# SQS, SNS and Event-Driven Design
"""
Decouple services with messages instead of direct calls: the producer drops a message and
moves on; consumers process it later, at their own speed, and can fail without taking the
producer down.

SQS (Simple Queue Service): a durable queue, one logical consumer group.
- `send_message` -> `receive_message` (long poll with WaitTimeSeconds up to 20) ->
  process -> `delete_message`. Not deleting = the message comes back.
- VISIBILITY TIMEOUT: after a receive the message is hidden for N seconds. If you do not
  delete it in time (crash, slow handler) it becomes visible again for another try.
  Set it to > your worst-case processing time.
- DEAD-LETTER QUEUE (DLQ): a second queue. A RedrivePolicy `maxReceiveCount=N` moves a
  message there after N failed receives, so ONE poison message cannot block or loop forever.
  Alarm on DLQ depth (m_14) and replay after fixing the bug.
- Standard queues: at-least-once delivery, best-effort ordering. FIFO queues (`.fifo`):
  ordering per MessageGroupId + dedup, lower throughput.

SNS (Simple Notification Service): publish/subscribe topics. One `publish` is copied to
every subscriber (SQS queues, Lambda, HTTPS, email). FAN-OUT = topic -> N queues, each
consumer team gets its own queue with its own retry/DLQ. SQS needs a QUEUE POLICY allowing
`sns.amazonaws.com` to `sqs:SendMessage` from that topic ARN. Unless you enable
`RawMessageDelivery`, the queue body is an SNS ENVELOPE (JSON with "Message" inside).

IDEMPOTENT CONSUMERS: delivery is at-least-once, so the same message WILL arrive twice
sometimes. Make the handler safe to repeat: dedupe on a stable id (message id or business
key) using a conditional write (`attribute_not_exists`, m_03) or a set/Redis key, or design
the operation itself to be idempotent ("set status=PAID", not "add 10 to balance").

Everything here runs on moto, no network.

Common mistakes
- Deleting the message BEFORE the work succeeded (lost on crash) or never deleting (loops).
- Visibility timeout shorter than processing time -> duplicate processing.
- No DLQ, or a DLQ nobody watches.
- Assuming exactly-once or in-order delivery on a standard queue.
- Forgetting the queue policy for SNS, so publishes silently go nowhere.
- Short polling in a tight loop: use WaitTimeSeconds=20 (long polling) and batch of 10.

Production notes
- Keep messages small (< 256 KB); put big payloads in S3 and send the key.
- Make consumers scale on queue depth / age of oldest message; Lambda event sources do.
- Version message schemas and ignore unknown fields so producers and consumers can deploy
  independently. Include a correlation id for tracing across services.
- Encrypt queues (SSE-SQS is on by default for new queues) and scope IAM to one queue ARN.

Cost notes
- SQS: first 1M requests/month free, then ~ $0.40 per million (each 64 KB chunk counts).
  Long polling and batching (10 messages per call) cut request count a lot.
- SNS: first 1M publishes free; SNS to SQS/Lambda delivery is free, SMS/email are not.
- A DLQ is a normal queue: you pay for it and messages expire (max 14 days retention).
"""

import json
import os
from collections.abc import Callable
from typing import Any
from unittest.mock import patch

import boto3
from moto import mock_aws

FAKE_AWS_ENV = {
    "AWS_ACCESS_KEY_ID": "testing",
    "AWS_SECRET_ACCESS_KEY": "testing",
    "AWS_SESSION_TOKEN": "testing",
    "AWS_DEFAULT_REGION": "us-east-1",
}


def queue_arn(sqs: Any, url: str) -> str:
    attrs = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn"])
    return attrs["Attributes"]["QueueArn"]


# Example 1: queue + DLQ via a redrive policy
def create_queue_with_dlq(sqs: Any, name: str, max_receive: int = 3) -> tuple[str, str]:
    dlq_url = sqs.create_queue(QueueName=f"{name}-dlq")["QueueUrl"]
    redrive = {"deadLetterTargetArn": queue_arn(sqs, dlq_url), "maxReceiveCount": max_receive}
    url = sqs.create_queue(
        QueueName=name,
        Attributes={"VisibilityTimeout": "30", "RedrivePolicy": json.dumps(redrive)},
    )["QueueUrl"]
    return url, dlq_url


# Example 2: fan-out: one SNS topic -> several SQS queues
def queue_policy_for_topic(q_arn: str, topic_arn: str) -> str:
    """Resource policy that lets ONLY this topic send to the queue (least privilege)."""
    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "sns.amazonaws.com"},
                    "Action": "sqs:SendMessage",
                    "Resource": q_arn,
                    "Condition": {"ArnEquals": {"aws:SourceArn": topic_arn}},
                }
            ],
        }
    )


def fan_out(sns: Any, sqs: Any, topic: str, queues: list[str]) -> tuple[str, dict[str, str]]:
    topic_arn = sns.create_topic(Name=topic)["TopicArn"]
    urls: dict[str, str] = {}
    for name in queues:
        url = sqs.create_queue(QueueName=name)["QueueUrl"]
        arn = queue_arn(sqs, url)
        policy = queue_policy_for_topic(arn, topic_arn)
        sqs.set_queue_attributes(QueueUrl=url, Attributes={"Policy": policy})
        sns.subscribe(TopicArn=topic_arn, Protocol="sqs", Endpoint=arn)
        urls[name] = url
    return topic_arn, urls


def unwrap_sns_message(body: str) -> str:
    """Queue bodies from SNS are an envelope; the payload is in the "Message" field."""
    envelope = json.loads(body)
    return envelope["Message"] if isinstance(envelope, dict) and "Message" in envelope else body


# Example 3: a consumer loop: delete only after success
def drain_queue(sqs: Any, url: str, handler: Callable[[str], None]) -> int:
    done = 0
    while True:
        resp = sqs.receive_message(QueueUrl=url, MaxNumberOfMessages=10, WaitTimeSeconds=0)
        messages = resp.get("Messages", [])
        if not messages:
            return done
        for msg in messages:
            try:
                handler(msg["Body"])
            except Exception as exc:  # leave it: it reappears after the visibility timeout
                print(f"  handler failed ({exc!r}); message will be retried")
                continue
            sqs.delete_message(QueueUrl=url, ReceiptHandle=msg["ReceiptHandle"])
            done += 1


# Example 4: idempotent processing (use a durable store in production, not a set)
def process_once(seen: set[str], message_id: str, work: Callable[[], None]) -> bool:
    if message_id in seen:
        return False  # duplicate delivery: skip
    work()
    seen.add(message_id)  # record AFTER success so a failure can be retried
    return True


def run_demo() -> None:
    sqs = boto3.client("sqs", region_name="us-east-1")
    sns = boto3.client("sns", region_name="us-east-1")

    url, dlq = create_queue_with_dlq(sqs, "orders", max_receive=2)
    sqs.send_message(QueueUrl=url, MessageBody="poison")
    for attempt in (1, 2, 3):  # VisibilityTimeout=0: instantly visible again, like a crash
        got = sqs.receive_message(QueueUrl=url, VisibilityTimeout=0).get("Messages", [])
        print(f"receive #{attempt}: {len(got)} message(s)")
    print("in DLQ:", len(sqs.receive_message(QueueUrl=dlq).get("Messages", [])))

    topic_arn, urls = fan_out(sns, sqs, "order-events", ["billing", "shipping"])
    sns.publish(TopicArn=topic_arn, Message=json.dumps({"order_id": 7}))
    seen: set[str] = set()
    for name, q in urls.items():
        for msg in sqs.receive_message(QueueUrl=q).get("Messages", []):
            payload = unwrap_sns_message(msg["Body"])
            ran = process_once(seen, f"{name}:{msg['MessageId']}", lambda: None)
            print(f"{name} got {payload} (processed={ran})")

    sqs.send_message(QueueUrl=urls["billing"], MessageBody="hello")
    print("drained:", drain_queue(sqs, urls["billing"], lambda body: print("  handled", body)))


if __name__ == "__main__":
    with patch.dict(os.environ, FAKE_AWS_ENV), mock_aws():
        run_demo()
