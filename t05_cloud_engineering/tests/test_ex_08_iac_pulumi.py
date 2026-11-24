import pytest

from _loader import load

ex = load("t05_cloud_engineering", "ex_08_iac_pulumi")


def test_merge_stack_config_deep_and_no_mutation():
    base = {"region": "us-east-1", "db": {"size": "small", "port": 5432}, "azs": ["a", "b"]}
    over = {"db": {"size": "large"}, "azs": ["c"], "extra": 1}
    merged = ex.merge_stack_config(base, over)
    assert merged == {
        "region": "us-east-1",
        "db": {"size": "large", "port": 5432},
        "azs": ["c"],
        "extra": 1,
    }
    assert base["db"] == {"size": "small", "port": 5432} and base["azs"] == ["a", "b"]
    assert over == {"db": {"size": "large"}, "azs": ["c"], "extra": 1}


def test_merge_does_not_share_nested_objects():
    base = {"db": {"port": 1}}
    merged = ex.merge_stack_config(base, {})
    merged["db"]["port"] = 2
    assert base["db"]["port"] == 1
    over = {"tags": {"a": "1"}}
    merged2 = ex.merge_stack_config({}, over)
    merged2["tags"]["a"] = "2"
    assert over["tags"]["a"] == "1"


def test_redact_secrets_nested():
    cfg = {
        "region": "us-east-1",
        "dbPassword": "hunter2",
        "db": {"API_KEY": "k", "host": "h", "auth": {"Token": "t"}},
        "users": [{"name": "a", "client_secret": "s"}, "plain"],
    }
    safe = ex.redact_secrets(cfg)
    assert safe == {
        "region": "us-east-1",
        "dbPassword": "[secret]",
        "db": {"API_KEY": "[secret]", "host": "h", "auth": {"Token": "[secret]"}},
        "users": [{"name": "a", "client_secret": "[secret]"}, "plain"],
    }
    assert cfg["dbPassword"] == "hunter2"  # original untouched
    assert cfg["users"][0]["client_secret"] == "s"


def test_required_config():
    cfg = {"region": "r", "vpc": "v", "other": 1}
    assert ex.required_config(cfg, ["region", "vpc"]) == {"region": "r", "vpc": "v"}
    with pytest.raises(ex.ConfigError) as info:
        ex.required_config(cfg, ["region", "subnets", "kms"])
    assert "subnets" in str(info.value) and "kms" in str(info.value)
    assert "region" not in str(info.value)


def test_plan_diff():
    current = {"a": {"x": 1}, "b": {"x": 1}, "gone": {}}
    desired = {"a": {"x": 1}, "b": {"x": 2}, "new2": {}, "new1": {}}
    assert ex.plan_diff(current, desired) == {
        "create": ["new1", "new2"],
        "update": ["b"],
        "delete": ["gone"],
        "same": ["a"],
    }
    assert ex.plan_diff({}, {}) == {"create": [], "update": [], "delete": [], "same": []}
