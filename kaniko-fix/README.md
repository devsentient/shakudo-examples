Setting up AWS Cluster
----------------------

1. followed instruction --> monorepo/infra_terraform/aws/README
2. update kube config to access k9s

```
aws eks update-kubeconfig \
  --region us-east-1 \
  --name shakudo-eks-cluster
```

---

Installing Shakudo Platform for EKS
-----------------------------------

1. ``helm upgrade --install shakudo-statics-prometheus . --namespace hyperplane-core --create-namespace``

Getting `CrashLoopBackOff` error but ignoring for now

<img width="1503" height="677" alt="Image" src="https://github.com/user-attachments/assets/27e97235-10bb-4b02-8f64-589efc0aa6d1" />

2. ``helm install shakudo-statics-certmanager . -n hyperplane-core``

<img width="1502" height="212" alt="Image" src="https://github.com/user-attachments/assets/544b2a1a-655d-44d7-8ad2-0e2f4f89af3a" />

3. Get context `kubectl config current-context`

and run commands

```
helm upgrade --install istio-base . --kube-context deploymentname --namespace istio-system --create-namespace -f values-override.yaml

helm upgrade --install istiod . --kube-context deploymentname --namespace istio-system --create-namespace -f values-override-ambient.yaml

helm upgrade --install istio-gateway . --kube-context deploymentname --namespace istio-system --create-namespace -f values-override.yaml
```

4. Install shakudo-platform

```
helm install shakudo-hyperplane . --namespace hyperplane-core --create-namespace --values valuesEks.yaml --debug
```

5. RoleBinding - prometheus

```
kubectl annotate rolebinding prometheus-k8s \
  -n monitoring \
  meta.helm.sh/release-name=shakudo-hyperplane \
  meta.helm.sh/release-namespace=hyperplane-core --overwrite

kubectl label rolebinding prometheus-k8s \
  -n monitoring \
  app.kubernetes.io/managed-by=Helm --overwrite

kubectl annotate role prometheus-k8s \
  -n monitoring \
  meta.helm.sh/release-name=shakudo-hyperplane \
  meta.helm.sh/release-namespace=hyperplane-core --overwrite

kubectl label role prometheus-k8s \
  -n monitoring \
  app.kubernetes.io/managed-by=Helm --overwrite
```

6. Getting the below error

```
Error: INSTALLATION FAILED: failed to create resource: Secret "gcr-service-account-jhub-42b5pz2e" is invalid: data[.dockerconfigjson]: Invalid value: "<secret contents redacted>": unexpected end of JSON input
helm.go:86: 2025-07-22 13:11:26.076091 -0400 EDT m=+36.046928293 [debug] Secret "gcr-service-account-jhub-42b5pz2e" is invalid: data[.dockerconfigjson]: Invalid value: "<secret contents redacted>": unexpected end of JSON input
failed to create resource
```

that's because monorepo/shakudo-platform/keys folder is missing 4 files

- hyperplane-service-account.json
- id_ed25519
- id_ed25519.pub
- sa-secret.json

7. register your domain
