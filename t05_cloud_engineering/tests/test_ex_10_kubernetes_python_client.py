import copy

import pytest

pytest.importorskip("kubernetes")
from kubernetes import client  # noqa: E402

from _loader import load  # noqa: E402

ex = load("t05_cloud_engineering", "ex_10_kubernetes_python_client")


def container(dep: dict) -> dict:
    return dep["spec"]["template"]["spec"]["containers"][0]


def test_build_configmap():
    cm = ex.build_configmap("cfg", {"A": "1"})
    assert cm["apiVersion"] == "v1" and cm["kind"] == "ConfigMap"
    assert cm["metadata"] == {"name": "cfg", "namespace": "default"}
    assert cm["data"] == {"A": "1"}
    assert ex.build_configmap("cfg", {}, "prod")["metadata"]["namespace"] == "prod"


def test_build_deployment_structure():
    dep = ex.build_deployment("api", "ghcr.io/acme/api:1.2.3", 3, 8000, {"B": "2", "A": "1"})
    assert dep["apiVersion"] == "apps/v1" and dep["kind"] == "Deployment"
    assert dep["metadata"]["name"] == "api"
    assert dep["metadata"]["labels"] == {"app": "api"}
    assert dep["spec"]["replicas"] == 3
    assert dep["spec"]["selector"]["matchLabels"] == {"app": "api"}
    assert dep["spec"]["template"]["metadata"]["labels"] == {"app": "api"}
    assert dep["spec"]["template"]["spec"]["securityContext"]["runAsNonRoot"] is True
    c = container(dep)
    assert c["name"] == "api" and c["image"] == "ghcr.io/acme/api:1.2.3"
    assert c["ports"][0]["containerPort"] == 8000
    assert c["env"] == [{"name": "A", "value": "1"}, {"name": "B", "value": "2"}]
    assert c["readinessProbe"]["httpGet"] == {"path": "/readyz", "port": 8000}
    assert c["livenessProbe"]["httpGet"] == {"path": "/healthz", "port": 8000}
    assert c["resources"]["requests"] == {"cpu": "100m", "memory": "128Mi"}
    assert c["resources"]["limits"] == {"cpu": "500m", "memory": "256Mi"}


def test_build_deployment_without_env_omits_key():
    assert "env" not in container(ex.build_deployment("api", "x:1", 1, 80))


def test_build_service_selector_matches_deployment():
    dep = ex.build_deployment("api", "x:1", 2, 8000)
    svc = ex.build_service("api", 80, 8000)
    assert svc["kind"] == "Service" and svc["apiVersion"] == "v1"
    assert svc["metadata"]["name"] == "api"
    assert svc["spec"]["type"] == "ClusterIP"
    assert svc["spec"]["selector"] == dep["spec"]["template"]["metadata"]["labels"]
    assert svc["spec"]["ports"] == [{"port": 80, "targetPort": 8000}]


def test_validate_good_manifest_is_clean():
    assert ex.validate_manifest(ex.build_deployment("api", "ghcr.io/acme/api:1.2.3", 2, 8000)) == []


def test_validate_reports_problems():
    dep = ex.build_deployment("api", "nginx:latest", 2, 80)
    bad = copy.deepcopy(dep)
    c = container(bad)
    del c["resources"], c["readinessProbe"], c["livenessProbe"]
    del bad["spec"]["template"]["spec"]["securityContext"]
    assert ex.validate_manifest(bad) == [
        "latest-tag:api",
        "no-liveness-probe:api",
        "no-readiness-probe:api",
        "no-resource-limits:api",
        "runs-as-root:api",
    ]


def test_validate_untagged_and_registry_port():
    assert ex.validate_manifest(ex.build_deployment("a", "nginx", 1, 80)) == ["latest-tag:a"]
    ok = ex.build_deployment("a", "registry.local:5000/team/app:2", 1, 80)
    assert ex.validate_manifest(ok) == []
    untagged = ex.build_deployment("a", "registry.local:5000/team/app", 1, 80)
    assert ex.validate_manifest(untagged) == ["latest-tag:a"]


def test_container_level_non_root_is_accepted():
    dep = ex.build_deployment("a", "x:1", 1, 80)
    del dep["spec"]["template"]["spec"]["securityContext"]
    assert ex.validate_manifest(dep) == ["runs-as-root:a"]
    container(dep)["securityContext"] = {"runAsNonRoot": True}
    assert ex.validate_manifest(dep) == []


def test_summarize_pods():
    pods = client.V1PodList(
        items=[
            client.V1Pod(
                metadata=client.V1ObjectMeta(name="web-2"),
                status=client.V1PodStatus(phase="Running"),
            ),
            client.V1Pod(metadata=client.V1ObjectMeta(name="web-1")),
            client.V1Pod(
                metadata=client.V1ObjectMeta(name="web-0"), status=client.V1PodStatus(phase="")
            ),
        ]
    )
    assert ex.summarize_pods(pods) == [
        ("web-0", "Unknown"),
        ("web-1", "Unknown"),
        ("web-2", "Running"),
    ]
