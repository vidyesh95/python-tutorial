"""Exercise 10: build and lint Kubernetes manifests offline (no cluster).

Tasks
1. build_configmap: a ConfigMap manifest dict.
2. build_deployment: a production-minded Deployment manifest dict.
3. build_service: a ClusterIP Service whose selector matches the Deployment.
4. validate_manifest: report common Deployment mistakes.
5. summarize_pods: summarize a V1PodList-like object.

You may build plain dicts, or `kubernetes.client` models serialized with
`client.ApiClient().sanitize_for_serialization(obj)` (that is what the lesson does).

Run: uv run pytest t05_cloud_engineering -k kubernetes
"""

from typing import Any

from kubernetes import client  # noqa: F401  (handy if you use models)


def build_configmap(name: str, data: dict[str, str], namespace: str = "default") -> dict[str, Any]:
    """Return {"apiVersion": "v1", "kind": "ConfigMap",
    "metadata": {"name": name, "namespace": namespace}, "data": data}.
    """
    raise NotImplementedError


def build_deployment(
    name: str, image: str, replicas: int, port: int, env: dict[str, str] | None = None
) -> dict[str, Any]:
    """Return an apps/v1 Deployment manifest dict (camelCase keys) with:

    - metadata.name = name; labels {"app": name} on metadata, spec.selector.matchLabels and
      the pod template metadata
    - spec.replicas = replicas
    - ONE container named `name` with `image`, containerPort `port`, env as a list of
      {"name": k, "value": v} sorted by name (omit the "env" key if env is empty/None)
    - readinessProbe httpGet path "/readyz" and livenessProbe httpGet path "/healthz", both on
      `port`
    - resources: requests {"cpu": "100m", "memory": "128Mi"}, limits {"cpu": "500m",
      "memory": "256Mi"}
    - pod-level securityContext {"runAsNonRoot": True}
    """
    raise NotImplementedError


def build_service(name: str, port: int, target_port: int) -> dict[str, Any]:
    """Return a v1 Service manifest: metadata.name = name, spec.type "ClusterIP", selector
    {"app": name}, and one port {"port": port, "targetPort": target_port}.
    """
    raise NotImplementedError


def validate_manifest(deployment: dict[str, Any]) -> list[str]:
    """Return a sorted list of unique issue strings, for every container in
    spec.template.spec.containers:

    - "latest-tag:<container>": image has no tag (a ':' after the last '/') or tag "latest"
    - "no-resource-limits:<container>": no non-empty resources.limits
    - "no-readiness-probe:<container>" / "no-liveness-probe:<container>": probe missing
    - "runs-as-root:<container>": runAsNonRoot is not True on the pod securityContext nor on
      the container's securityContext
    """
    raise NotImplementedError


def summarize_pods(pod_list: Any) -> list[tuple[str, str]]:
    """Given an object with `.items`, each with `.metadata.name` and `.status.phase`, return
    [(name, phase), ...] sorted by name. If status is None or phase is empty use "Unknown".
    """
    raise NotImplementedError
