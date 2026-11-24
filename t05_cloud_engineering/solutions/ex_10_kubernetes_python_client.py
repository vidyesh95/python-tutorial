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

from kubernetes import client


def _to_dict(obj: Any) -> dict[str, Any]:
    return client.ApiClient().sanitize_for_serialization(obj)


def build_configmap(name: str, data: dict[str, str], namespace: str = "default") -> dict[str, Any]:
    """Return {"apiVersion": "v1", "kind": "ConfigMap",
    "metadata": {"name": name, "namespace": namespace}, "data": data}.
    """
    return _to_dict(
        client.V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            data=data,
        )
    )


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
    labels = {"app": name}
    container = client.V1Container(
        name=name,
        image=image,
        ports=[client.V1ContainerPort(container_port=port)],
        env=[client.V1EnvVar(name=k, value=v) for k, v in sorted((env or {}).items())] or None,
        readiness_probe=client.V1Probe(
            http_get=client.V1HTTPGetAction(path="/readyz", port=port), period_seconds=5
        ),
        liveness_probe=client.V1Probe(
            http_get=client.V1HTTPGetAction(path="/healthz", port=port), period_seconds=10
        ),
        resources=client.V1ResourceRequirements(
            requests={"cpu": "100m", "memory": "128Mi"},
            limits={"cpu": "500m", "memory": "256Mi"},
        ),
    )
    return _to_dict(
        client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(name=name, labels=labels),
            spec=client.V1DeploymentSpec(
                replicas=replicas,
                selector=client.V1LabelSelector(match_labels=labels),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels=labels),
                    spec=client.V1PodSpec(
                        containers=[container],
                        security_context=client.V1PodSecurityContext(run_as_non_root=True),
                    ),
                ),
            ),
        )
    )


def build_service(name: str, port: int, target_port: int) -> dict[str, Any]:
    """Return a v1 Service manifest: metadata.name = name, spec.type "ClusterIP", selector
    {"app": name}, and one port {"port": port, "targetPort": target_port}.
    """
    return _to_dict(
        client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=client.V1ObjectMeta(name=name),
            spec=client.V1ServiceSpec(
                type="ClusterIP",
                selector={"app": name},
                ports=[client.V1ServicePort(port=port, target_port=target_port)],
            ),
        )
    )


def validate_manifest(deployment: dict[str, Any]) -> list[str]:
    """Return a sorted list of unique issue strings, for every container in
    spec.template.spec.containers:

    - "latest-tag:<container>": image has no tag (a ':' after the last '/') or tag "latest"
    - "no-resource-limits:<container>": no non-empty resources.limits
    - "no-readiness-probe:<container>" / "no-liveness-probe:<container>": probe missing
    - "runs-as-root:<container>": runAsNonRoot is not True on the pod securityContext nor on
      the container's securityContext
    """
    issues: set[str] = set()
    pod = deployment["spec"]["template"]["spec"]
    pod_nonroot = pod.get("securityContext", {}).get("runAsNonRoot") is True
    for c in pod["containers"]:
        name = c["name"]
        image = c["image"]
        last = image.rsplit("/", 1)[-1]
        if ":" not in last or last.endswith(":latest"):
            issues.add(f"latest-tag:{name}")
        if not c.get("resources", {}).get("limits"):
            issues.add(f"no-resource-limits:{name}")
        if "readinessProbe" not in c:
            issues.add(f"no-readiness-probe:{name}")
        if "livenessProbe" not in c:
            issues.add(f"no-liveness-probe:{name}")
        if not (pod_nonroot or c.get("securityContext", {}).get("runAsNonRoot") is True):
            issues.add(f"runs-as-root:{name}")
    return sorted(issues)


def summarize_pods(pod_list: Any) -> list[tuple[str, str]]:
    """Given an object with `.items`, each with `.metadata.name` and `.status.phase`, return
    [(name, phase), ...] sorted by name. If status is None or phase is empty use "Unknown".
    """
    return sorted(
        (p.metadata.name, p.status.phase if p.status and p.status.phase else "Unknown")
        for p in pod_list.items
    )
