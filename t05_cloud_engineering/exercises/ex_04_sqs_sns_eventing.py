"""Exercise 04: SQS queues, DLQs, SNS fan-out and idempotent consumers.

`sqs` / `sns` are boto3 clients (tests pass moto-backed ones).

Tasks
1. create_queue_with_dlq: main queue whose RedrivePolicy points at a DLQ.
2. fan_out: topic -> several SQS queues.
3. unwrap_sns_message: extract the payload from an SNS envelope.
4. drain_queue: consume until empty, deleting only after the handler succeeds.
5. process_once: idempotent processing keyed by message id.

Run: uv run pytest t05_cloud_engineering -k sqs_sns
"""

import json  # noqa: F401  (handy for tasks 1 and 3)
from collections.abc import Callable
from typing import Any


def create_queue_with_dlq(sqs: Any, name: str, max_receive: int = 3) -> tuple[str, str]:
    """Create `{name}-dlq`, then `name` with Attributes
    {"VisibilityTimeout": "30", "RedrivePolicy": <JSON string>} where the policy has
    "deadLetterTargetArn" (the DLQ's QueueArn) and "maxReceiveCount" (an int).
    Return (queue_url, dlq_url).
    """
    raise NotImplementedError


def fan_out(sns: Any, sqs: Any, topic: str, queues: list[str]) -> tuple[str, dict[str, str]]:
    """Create SNS topic `topic` and one SQS queue per name in `queues`, and subscribe every
    queue (Protocol "sqs", Endpoint = the queue's QueueArn) to the topic.

    Return (topic_arn, {queue_name: queue_url}).
    """
    raise NotImplementedError


def unwrap_sns_message(body: str) -> str:
    """If `body` is a JSON object with a "Message" key (an SNS envelope), return that value;
    otherwise return `body` unchanged (also when it is not valid JSON or not an object).
    """
    raise NotImplementedError


def drain_queue(sqs: Any, url: str, handler: Callable[[str], None]) -> int:
    """Receive (MaxNumberOfMessages=10, WaitTimeSeconds=0) until the queue returns nothing.

    For each message call handler(body). If it returns normally delete the message and count
    it; if it raises, do NOT delete it (it will be retried later) and continue with the next.
    Return the number of successfully processed messages.
    """
    raise NotImplementedError


def process_once(seen: set[str], message_id: str, work: Callable[[], None]) -> bool:
    """Idempotent processing. If `message_id` is already in `seen` return False without
    calling `work`. Otherwise call work(); only after it succeeds add the id to `seen` and
    return True. If work() raises, the exception propagates and the id is NOT recorded.
    """
    raise NotImplementedError
