# Kubernetes with the Python Client
"""
Kubernetes (k8s) runs containers across a cluster of machines. You DECLARE the desired
state in manifests (YAML/JSON objects); controllers continuously make reality match it.

Core objects
- POD: one or more containers sharing network/storage; the unit that runs. Ephemeral.
- DEPLOYMENT: keeps N identical replicas of a pod running and does rolling updates.
- SERVICE: a stable virtual IP/DNS name load-balancing across the pods matching a label
  SELECTOR (`app: taskboard`). Types: ClusterIP (internal), LoadBalancer (public).
- CONFIGMAP / SECRET: configuration injected as env vars or files. (Secrets are only
  base64, not encrypted by default: use an external store + CSI driver, see m_13.)
- NAMESPACE: a virtual cluster for isolation; RBAC (Role/RoleBinding) controls who can do what.

Production-minded container spec (all shown in the builders below)
- RESOURCES: `requests` (what the scheduler reserves) and `limits` (hard cap). Without them one
  pod can starve a node. Exceeding the memory limit gets the pod OOM-killed.
- PROBES: `readinessProbe` gates traffic (pod removed from the Service until ready);
  `livenessProbe` restarts a stuck container. Point them at `/readyz` and `/healthz` from t04.
- SECURITY CONTEXT: `runAsNonRoot: true`, no privilege escalation, read-only root filesystem.
- Pin image tags (never `:latest`), set `replicas >= 2` for availability.

The Python client (`pip install kubernetes`, installed in the cloud group)
- Models: `client.V1Deployment`, `V1Service`, `V1ConfigMap`, ... mirror the API objects.
  `client.ApiClient().sanitize_for_serialization(obj)` turns a model into the plain dict /
  JSON that `kubectl apply -f` accepts, WITHOUT any cluster. We use that to build and test
  manifests offline.
- APIs: `CoreV1Api` (pods, services, configmaps), `AppsV1Api` (deployments), ...
- Auth: `config.load_kube_config()` (reads `$KUBECONFIG` / ~/.kube/config, local dev) or
  `config.load_incluster_config()` (inside a pod: uses the pod's ServiceAccount token).
- Errors: `kubernetes.client.exceptions.ApiException` has `.status` (403 = RBAC denied,
  404 = not found, 409 = conflict/already exists) and `.reason`.
- Real cluster calls in this lesson run ONLY if the KUBECONFIG env var is set.

Common mistakes
- No resource requests/limits; `latest` tags; no probes (rolling updates send traffic to
  pods that are not ready, giving 502s).
- Selector labels not matching pod template labels (Service has no endpoints).
- Liveness probe too aggressive or doing deep checks (restart storms when the DB blips).
- Putting secrets in ConfigMaps or committing Secret YAML to git.
- Giving the app ServiceAccount cluster-admin; scope a Role to its namespace.

Production notes
- Treat manifests as build artifacts: generate, validate (kubeconform, policy checks), review,
  apply with GitOps (Argo CD / Flux) or CI (m_11) instead of ad-hoc `kubectl`.
- Add a HorizontalPodAutoscaler, a PodDisruptionBudget and anti-affinity across zones.
- Use `kubectl diff` / server-side dry-run (`dry_run="All"`) before applying.
- Managed control planes: EKS (AWS) and GKE (GCP). Often ECS/Cloud Run is simpler (capstone).

Cost notes
- EKS control plane ~ $0.10/hour per cluster (about $73/month) plus nodes; GKE Autopilot
  bills per pod resource requests. Over-requesting CPU/memory is paying for idle capacity.
- Delete test clusters; a forgotten cluster and its load balancers bill 24/7.
"""

import os
from typing import Any

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException


# Example 1: manifests as typed models, serialized to plain dicts
def build_configmap(
    name: str, data: dict[str, str], namespace: str = "default"
) -> client.V1ConfigMap:
    return client.V1ConfigMap(
        api_version="v1",
        kind="ConfigMap",
        metadata=client.V1ObjectMeta(name=name, namespace=namespace),
        data=data,
    )


def build_deployment(
    name: str, image: str, replicas: int, port: int, env: dict[str, str] | None = None
) -> client.V1Deployment:
    labels = {"app": name}
    container = client.V1Container(
        name=name,
        image=image,
        ports=[client.V1ContainerPort(container_port=port)],
        env=[client.V1EnvVar(name=k, value=v) for k, v in sorted((env or {}).items())],
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
        security_context=client.V1SecurityContext(
            allow_privilege_escalation=False, read_only_root_filesystem=True
        ),
    )
    return client.V1Deployment(
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


def build_service(name: str, port: int, target_port: int) -> client.V1Service:
    return client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(name=name),
        spec=client.V1ServiceSpec(
            type="ClusterIP",
            selector={"app": name},  # must equal the pod template labels
            ports=[client.V1ServicePort(port=port, target_port=target_port)],
        ),
    )


def to_manifest(obj: Any) -> dict[str, Any]:
    """Model -> plain dict (camelCase keys, None fields dropped). No cluster needed."""
    return client.ApiClient().sanitize_for_serialization(obj)


# Example 2: lint a Deployment manifest (a tiny policy check)
def validate_manifest(deployment: dict[str, Any]) -> list[str]:
    issues: set[str] = set()
    pod = deployment["spec"]["template"]["spec"]
    pod_nonroot = pod.get("securityContext", {}).get("runAsNonRoot") is True
    for c in pod["containers"]:
        name = c["name"]
        image = c["image"]
        if ":" not in image.rsplit("/", 1)[-1] or image.endswith(":latest"):
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


# Example 3: summarize a pod list (works for real V1PodList or a hand-built one)
def summarize_pods(pod_list: Any) -> list[tuple[str, str]]:
    return sorted(
        (p.metadata.name, (p.status.phase if p.status and p.status.phase else "Unknown"))
        for p in pod_list.items
    )


# Example 4: real cluster access, only with KUBECONFIG set
def list_pods_in_cluster(namespace: str = "default") -> list[tuple[str, str]]:
    config.load_kube_config(config_file=os.environ["KUBECONFIG"])
    try:
        return summarize_pods(client.CoreV1Api().list_namespaced_pod(namespace))
    except ApiException as exc:
        if exc.status == 403:
            raise PermissionError(f"RBAC: not allowed to list pods in {namespace!r}") from exc
        raise


if __name__ == "__main__":
    deployment = to_manifest(
        build_deployment(
            "taskboard", "ghcr.io/acme/taskboard:1.4.2", 2, 8000, {"LOG_LEVEL": "info"}
        )
    )
    service = to_manifest(build_service("taskboard", 80, 8000))
    configmap = to_manifest(build_configmap("taskboard-config", {"LOG_LEVEL": "info"}))
    print("kinds:", [m["kind"] for m in (configmap, deployment, service)])
    print("replicas:", deployment["spec"]["replicas"])
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    print(
        "probes:",
        container["readinessProbe"]["httpGet"]["path"],
        container["livenessProbe"]["httpGet"]["path"],
    )
    print("resource limits:", container["resources"]["limits"])
    print(
        "service selector matches pods:",
        service["spec"]["selector"] == deployment["spec"]["template"]["metadata"]["labels"],
    )
    print("issues (good):", validate_manifest(deployment))

    sloppy = to_manifest(build_deployment("x", "nginx:latest", 1, 80))
    del sloppy["spec"]["template"]["spec"]["containers"][0]["resources"]
    del sloppy["spec"]["template"]["spec"]["containers"][0]["readinessProbe"]
    print("issues (sloppy):", validate_manifest(sloppy))

    fake_pods = client.V1PodList(
        items=[
            client.V1Pod(
                metadata=client.V1ObjectMeta(name="web-2"),
                status=client.V1PodStatus(phase="Running"),
            ),
            client.V1Pod(metadata=client.V1ObjectMeta(name="web-1")),
        ]
    )
    print("pods:", summarize_pods(fake_pods))

    if os.getenv("KUBECONFIG"):
        print("live pods:", list_pods_in_cluster())
    else:
        print("KUBECONFIG not set: skipping real cluster calls")
