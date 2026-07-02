# Kubernetes Conventions

Standards for writing Kubernetes manifests, Helm charts, and operating clusters. Covers common patterns and anti-patterns.
Based on [Kubernetes Documentation](https://kubernetes.io/docs/home/), [Configuration Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/), and [Helm Best Practices](https://helm.sh/docs/chart_best_practices/).

## Manifest Basics

> Ref: [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/), [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)

Always set these fields Kubernetes won't error without them, but they matter in production:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: production # Always explicit never rely on default namespace
  labels:
    app: api
    version: '1.2.0'
    component: backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: api
          image: myorg/api:1.2.0 # Never :latest in production
          resources:
            requests:
              cpu: '100m'
              memory: '128Mi'
            limits:
              memory: '256Mi' # CPU limit intentionally omitted (causes throttling)
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 15
          readinessProbe:
            httpGet:
              path: /readyz
              port: 8080
            periodSeconds: 5
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            readOnlyRootFilesystem: true
            allowPrivilegeEscalation: false
```

## Resource Requests and Limits

> Ref: [Managing Resources](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/), [CPU limit considered harmful](https://home.robusta.dev/blog/stop-using-cpu-limits)

**Rule**: Always set `requests`. Set `limits` for memory only never for CPU.

|                 | Why                                                                             |
| --------------- | ------------------------------------------------------------------------------- |
| CPU limits      | Cause CPU throttling even when node has capacity degrades latency unpredictably |
| Memory limits   | Prevent OOM on other pods containers restart instead of degrading the node      |
| CPU requests    | Enable scheduler to place pods correctly                                        |
| Memory requests | Protect against eviction under pressure                                         |

## Probes

> Ref: [Configure Liveness, Readiness and Startup Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

Three distinct probes use all three when the application supports it:

| Probe            | Fails →                            | Use for                                                  |
| ---------------- | ---------------------------------- | -------------------------------------------------------- |
| `livenessProbe`  | Container restart                  | Deadlock, unrecoverable state                            |
| `readinessProbe` | Remove from Service endpoints      | Not yet ready to receive traffic                         |
| `startupProbe`   | Container restart (during startup) | Slow-starting apps (prevents liveness from killing them) |

## ConfigMaps and Secrets

> Ref: [ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/), [Secrets](https://kubernetes.io/docs/concepts/configuration/secret/), [External Secrets Operator](https://external-secrets.io/)

```yaml
# ConfigMap non-sensitive config
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
data:
  LOG_LEVEL: "info"
  PORT: "8080"

# Reference in pod
envFrom:
  - configMapRef:
      name: api-config

# Secret sensitive values (base64 encoded, not encrypted at rest by default)
# In production: use External Secrets Operator + Vault/AWS Secrets Manager
apiVersion: v1
kind: Secret
metadata:
  name: api-secrets
type: Opaque
stringData:           # Use stringData no manual base64 encoding
  DATABASE_URL: "postgres://user:pass@host/db"
```

**Rule**: Native Kubernetes Secrets are base64, not encrypted. Use External Secrets Operator or Sealed Secrets for real secret management.

## RBAC

> Ref: [RBAC Authorization](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

```yaml
# Service account per workload
apiVersion: v1
kind: ServiceAccount
metadata:
  name: api
  namespace: production
---
# Role namespace-scoped permissions
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: api-role
  namespace: production
rules:
  - apiGroups: ['']
    resources: ['configmaps']
    verbs: ['get', 'list'] # Least privilege only what the app needs
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: api-rolebinding
  namespace: production
subjects:
  - kind: ServiceAccount
    name: api
roleRef:
  kind: Role
  name: api-role
  apiGroup: rbac.authorization.k8s.io
```

**Rule**: One ServiceAccount per workload. Use `Role`/`RoleBinding` (namespace-scoped) unless cluster-wide is explicitly required.

## Helm

> Ref: [Helm Documentation](https://helm.sh/docs/), [Chart Best Practices](https://helm.sh/docs/chart_best_practices/)

```
chart/
├── Chart.yaml
├── values.yaml        # Default values
├── values-prod.yaml   # Production overrides
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    └── _helpers.tpl   # Named templates and helpers
```

```yaml
# values.yaml parameterize what changes between environments
replicaCount: 2
image:
  repository: myorg/api
  tag: '' # Override at deploy time: --set image.tag=1.2.0
  pullPolicy: IfNotPresent

resources:
  requests:
    cpu: 100m
    memory: 128Mi
```

**Rules:**

- Never hardcode environment-specific values in `templates/` put them in `values.yaml`
- Use `helm lint` and `helm template` in CI before deploying
- Pin chart dependencies in `Chart.lock`

## Troubleshooting Workflow

```bash
# Pod not starting
kubectl get pods -n <namespace>
kubectl describe pod <pod-name> -n <namespace>   # Events section shows why
kubectl logs <pod-name> -n <namespace> --previous  # Logs from crashed container

# Service not reachable
kubectl get endpoints <service-name> -n <namespace>  # Empty = no pods matching selector
kubectl get pods -n <namespace> -l app=<label>       # Verify label match

# Resource issues
kubectl top pods -n <namespace>
kubectl top nodes

# Debug with ephemeral container (K8s 1.25+)
kubectl debug -it <pod-name> -n <namespace> --image=busybox --target=<container>

# Port-forward for local testing
kubectl port-forward svc/<service> 8080:80 -n <namespace>
```

## Anti-Patterns to Flag

- `:latest` image tag in Deployment non-deterministic; can't roll back reliably because the scheduler can't distinguish versions
- No resource `requests` scheduler can't make informed placement decisions; pods get evicted first under pressure (BestEffort QoS)
- CPU `limits` set causes throttling even when node has spare capacity; degrades latency unpredictably. Remove unless you have a measured reason
- Running as root (`runAsNonRoot: false`) a container escape vulnerability becomes a full node compromise
- Storing secrets in ConfigMaps or hardcoded env vars ConfigMaps are not encrypted; use Secrets with encryption at rest or External Secrets Operator
- Using the `default` namespace for workloads no isolation, no RBAC boundaries, harder to operate in production
- `kubectl apply` in CI without dry-run + review one-way operation in production; always `--dry-run=server` first
- Missing `PodDisruptionBudget` for critical services node drains and cluster upgrades will take all replicas down simultaneously
- No `NetworkPolicy` all pods can communicate in all namespaces by default; restrict with explicit ingress/egress rules ([Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/))
- Liveness probe too aggressive (low `initialDelaySeconds`, low `periodSeconds`) kills containers before they finish starting; use `startupProbe` for slow apps

## Self-Check

- [ ] Every container has `resources.requests` for CPU and memory
- [ ] Memory `limits` set; CPU `limits` omitted (unless explicitly justified)
- [ ] `readinessProbe` and `livenessProbe` configured; `startupProbe` for slow-starting apps
- [ ] All containers run as non-root (`runAsNonRoot: true`, `allowPrivilegeEscalation: false`)
- [ ] Namespace explicitly set no workloads in `default`
- [ ] Image tags pinned to version (no `:latest`)
- [ ] Secrets managed via External Secrets Operator or Sealed Secrets not plain K8s Secrets with literals
- [ ] RBAC: one ServiceAccount per workload, least-privilege Role/RoleBinding
- [ ] `PodDisruptionBudget` configured for services with `replicas > 1`
- [ ] Helm: `helm lint` + `helm template` pass in CI before deploy
- [ ] `NetworkPolicy` restricts traffic to only required paths
