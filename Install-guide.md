# Langfuse
This is a Helm chart to install a **Shakudo-managed Langfuse stack component**.  
This is **Phase 1**, so you still need to:
- Add the **GraphQL mutation** manually.
- Add **whitelist redirect URIs** to **Keycloak** manually.

---

## **📦 Management Scripts**
This installation guide is complemented by automated management scripts located in `scripts/` directory:

- **langfuse-health-check.sh** - Comprehensive health validation after installation
- **langfuse-minio-configurator.sh** - Automated MinIO setup and configuration
- **langfuse-nextauth-configurator.sh** - Automated NextAuth URL configuration based on cluster domain
- **langfuse-clickhouse-manager.sh** - ClickHouse management and troubleshooting

For detailed documentation, see:
- **`scripts/README.md`** - Complete guide for all management scripts (usage, troubleshooting, workflows)

---

## **Pre-Installation Steps**
Before installing, ensure the following:

### **1️⃣ Generate Required Secrets and Configure NextAuth**

#### Generate Secrets
Run the following commands to generate necessary secrets:

```sh
openssl rand -base64 16  # Generate SALT
openssl rand -base64 32  # Generate SECRET
openssl rand -hex 32     # Generate ENCRYPTION_KEY
```

Add the generated values to the **valuesOverride.yaml** file:

```yaml
langfuse:
  nextauth:
    secret: "<SECRET>"
  salt: "<SALT>"
  additionalEnv:
    - name: "ENCRYPTION_KEY"
      value: "<ENCRYPTION_KEY>"
```

> **⚠️ Important:** Do **NOT** include `ENCRYPTION_KEY` in the default values file, as **Langfuse will pick up the unset default value** and the pod will enter `CrashLoopBackOff`.

#### Configure NextAuth URL (Recommended)
Use the automated NextAuth configurator to set the correct URL based on your cluster's domain:

```sh
cd scripts/
./langfuse-nextauth-configurator.sh \
  -f ../langfuse/valuesOverride.yaml \
  -r <release-name> \
  -k /path/to/kubeconfig.txt
```

The script will:
- ✅ Auto-detect the cluster domain from `hyperplane-settings` ConfigMap
- ✅ Construct the correct NextAuth URL (e.g., `https://<release-name>.<domain>`)
- ✅ Update valuesOverride.yaml with the correct configuration
- ✅ Backup original configuration file

**Example:**
For release `langfuse-v3` in domain `test3.canopyhub.io`, the script will configure:
```yaml
langfuse:
  nextauth:
    url: "https://langfuse-v3.test3.canopyhub.io"
```

> **Note:** If the script cannot auto-detect the domain, you can specify it manually:
> ```sh
> ./langfuse-nextauth-configurator.sh -f values.yaml -r langfuse-v3 -d test3.canopyhub.io
> ```

For detailed usage, see `scripts/README.md` (NextAuth Configurator section)

---

### **2️⃣ Create Required MinIO Buckets (If Not Already Created)**

#### Option A: Automated Setup (Recommended)
Use the MinIO configurator script to automatically set up buckets and configure valuesOverride.yaml:

```sh
cd scripts/
./langfuse-minio-configurator.sh \
  -f ../langfuse/valuesOverride.yaml \
  -n <namespace> \
  -k /path/to/kubeconfig.txt
```

The script will:
- ✅ Check existing MinIO configuration in valuesOverride.yaml
- ✅ Auto-discover MinIO installation in your cluster
- ✅ Create required buckets: langfuse-v3-storage, langfuse-v3-export, langfuse-v3-media
- ✅ Create MinIO user and policy
- ✅ Update valuesOverride.yaml with correct configuration
- ✅ Backup original configuration file

For detailed usage, see `scripts/README.md` (MinIO Configurator section)

#### Option B: Manual Setup
If MinIO is being used for **media, batch exports, or event storage**, **ensure the following S3 buckets exist** **before installation**:

1. langfuse-v3-storage
2. langfuse-v3-export
3. langfuse-v3-media

Ensure MinIO is correctly configured in **valuesOverride.yaml** by verifying the values with prefix `LANGFUSE_S3_`

---

### **Configure ClickHouse**
Ensure that the ClickHouse instance is correctly set up.  
The following **valuesOverride.yaml** snippet should match your ClickHouse deployment:

```yaml
clickhouse:
  image:
    tag: 24.11.1-debian-12-r0
  auth:
    username: "clickhouse.auth.username.changeme"
    password: "clickhouse.auth.password.changeme"
  resources:
    requests:
      cpu: 1
      memory: 2Gi
    limits:
      cpu: 2
      memory: 4Gi
```

Verify that ClickHouse credentials match your **ClickHouse migration URL** in **Langfuse**:

```yaml
langfuse:
  additionalEnv:
    - name: "CLICKHOUSE_MIGRATION_URL"
      value: "clickhouse://langfuse-v3-clickhouse.hyperplane-langfuse-v3:9000"
    - name: "CLICKHOUSE_URL"
      value: "http://langfuse-v3-clickhouse.hyperplane-langfuse-v3:8123"
    - name: "CLICKHOUSE_USER"
      value: "clickhouse.auth.username.changeme"
    - name: "CLICKHOUSE_PASSWORD"
      value: "clickhouse.auth.password.changeme"
```

---

### **Set Up Redis (Valkey)**
Langfuse requires Redis (Valkey) for caching. Ensure Redis is configured in **valuesOverride.yaml**:

```yaml
valkey:
  auth:
    password: valkey.auth.password.changeme
  master:
    resources: 
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 200m
        memory: 500Mi
```

---

### **Configure Keycloak Authentication**
By default, **username/password authentication is disabled**, and Keycloak is used instead.  
Ensure the following values are set in **valuesOverride.yaml**:

```yaml
langfuse:
  additionalEnv:
    - name: AUTH_DISABLE_USERNAME_PASSWORD
      value: "true"
    - name: AUTH_KEYCLOAK_CLIENT_ID
      value: "istio"
    - name: AUTH_KEYCLOAK_CLIENT_SECRET
      value: "123456789"
    - name: AUTH_KEYCLOAK_ISSUER
      value: "http://keycloak.hyperplane-core.svc.cluster.local:8080/auth/realms/Hyperplane"
```

> **Ensure that Keycloak is running and correctly configured before deploying Langfuse!**

---

## **Helm Install**
Once all **pre-requisites** are configured, deploy Langfuse using Helm:

```sh
helm upgrade --install langfuse-v3 ./langfuse \
  --namespace hyperplane-langfuse-v3 \
  --values ./langfuse/valuesOverride.yaml \
  --create-namespace \
  --kube-context=CONTEXT
```

> **💡 Note:** If upgrading from an older Langfuse version, make sure to **migrate existing data** before proceeding.

---

## **✅ Post-Installation Verification**

After installation, it's **highly recommended** to run the comprehensive health check to validate all components:

### **Run Health Check**
```sh
cd scripts/
./langfuse-health-check.sh \
  -n hyperplane-langfuse-v3 \
  -r langfuse-v3 \
  -k /path/to/kubeconfig.txt \
  --verbose
```

### **What the Health Check Validates**
The health check performs 12+ comprehensive checks:
- ✅ Namespace and resource existence
- ✅ Deployment health (web, worker)
- ✅ StatefulSet health (PostgreSQL, ClickHouse, Redis)
- ✅ Pod status and restart counts
- ✅ Service and ingress configuration
- ✅ PostgreSQL connection and migrations
- ✅ ClickHouse connection and migrations
- ✅ MinIO/S3 configuration
- ✅ Redis cache connectivity

### **Auto-Fix Common Issues**
If issues are detected, use the `--fix` flag to automatically remediate common problems:

```sh
./langfuse-health-check.sh \
  -n hyperplane-langfuse-v3 \
  -r langfuse-v3 \
  -k /path/to/kubeconfig.txt \
  --fix
```

The `--fix` flag will automatically:
- Restart unhealthy deployments and statefulsets
- Recreate failed PostgreSQL pods
- Recreate failed Redis pods

> **Note:** ClickHouse and MinIO issues require specialized scripts (see Troubleshooting section below)

For detailed documentation, see `scripts/README.md` (Health Check section)

---

## **Adding the License Body**
If using **Langfuse Enterprise**, add your **license key** in **valuesOverride.yaml**:

```yaml
langfuse:
  licenseKey: "<LICENSE_KEY>"
```

Then apply the GraphQL mutation (refer to the **Enterprise License Setup** section).

---

## **🚨 Troubleshooting**

### **ClickHouse Issues**

If ClickHouse has dirty migration flags:
```sh
cd scripts/
./langfuse-clickhouse-manager.sh \
  -n hyperplane-langfuse-v3 \
  -r langfuse-v3 \
  -k /path/to/kubeconfig.txt \
  --fix \
  --restart-deployments
```

### **MinIO Configuration Issues**

If MinIO is not configured or needs verification:
```sh
cd scripts/
./langfuse-minio-configurator.sh \
  -f ../langfuse/valuesOverride.yaml \
  -n hyperplane-langfuse-v3 \
  -k /path/to/kubeconfig.txt
```

### **General Health Issues**

Run health check with auto-fix:
```sh
cd scripts/
./langfuse-health-check.sh \
  -n hyperplane-langfuse-v3 \
  -r langfuse-v3 \
  -k /path/to/kubeconfig.txt \
  --fix \
  --verbose
```

For detailed troubleshooting, see:
- **`scripts/README.md`** - Complete troubleshooting guide for all components (Health Check, ClickHouse, MinIO)

---

## **Uninstalling Langfuse**
To completely remove Langfuse:

```sh
helm uninstall langfuse-v3 --namespace hyperplane-langfuse-v3 --kube-context YOURCONTEXT
```

### **Remove Persistent Data**
To avoid orphaned storage, **manually delete Persistent Volume Claims (PVCs):**
```sh
kubectl delete pvc -n hyperplane-langfuse-v3 --all
```