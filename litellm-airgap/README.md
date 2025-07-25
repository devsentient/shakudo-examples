✅ Setup Summary: Serving Static Swagger UI via EnvoyFilter + BusyBox HTTP Server

1. EnvoyFilter to Intercept Requests and Return Static HTML
   Configured an EnvoyFilter to intercept inbound requests on port 4000 and return a static HTML response for the Swagger UI when visiting the LiteLLM root domain (litellm.`<domain>`).

<details> <summary>Click to expand EnvoyFilter YAML</summary>

```
{{- $configmapObject := (lookup "v1" "ConfigMap" "hyperplane-core" "hyperplane-settings") | default dict }}
{{- $cmData := (get $configmapObject "data") | default dict }}
{{- $domainName := (get $cmData "HYPERPLANE_DOMAIN") }}

apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: return-static-html
  namespace: {{ .Release.Namespace }}
spec:
  workloadSelector:
    labels:
      {{- include "litellm.selectorLabels" . | nindent 6 }}
  configPatches:
    - applyTo: HTTP_FILTER
      match:
        context: SIDECAR_INBOUND
        listener:
          portNumber: 4000
          filterChain:
            filter:
              name: "envoy.filters.network.http_connection_manager"
      patch:
        operation: INSERT_BEFORE
        value:
          name: envoy.filters.http.lua
          typed_config:
            "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
            inlineCode: |
              function envoy_on_request(request_handle)
                local host = request_handle:headers():get(":authority")
                local path = request_handle:headers():get(":path")
                if host == "litellm.{{ $domainName }}" and (path == "/" or path == "/?panel=home") then
                  local html = [[
                    <!DOCTYPE html>
                    <html>
                    <head>
                      <link type="text/css" rel="stylesheet" href="/swagger-ui.css">
                      <link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
                      <title>LiteLLM API - Swagger UI</title>
                    </head>
                    <body>
                    <div id="swagger-ui"></div>
                    <h2>LiteLLM API</h2>
                    <p><strong>Version:</strong> 1.71.1</p>
                    <p><strong>OpenAPI:</strong> 3.1</p>
                    <p><code>/openapi.json</code></p>
                    <p>
                     Proxy Server to call 100+ LLMs in the OpenAI format. Customize Swagger Docs.
                    </p>
                    <p>
                     <a href="/sso/key/generate">LiteLLM Admin Panel on <code>/ui</code></a><br>
                     <a href="https://models.litellm.ai/" target="_blank">LiteLLM Model Cost Map</a>
                    </p>
                    <script src="/swagger-ui-bundle.js"></script>
                    <script>
                      const ui = SwaggerUIBundle({
                        dom_id: '#swagger-ui',
                        layout: 'BaseLayout',
                        deepLinking: true,
                        showExtensions: true,
                        showCommonExtensions: true,
                        oauth2RedirectUrl: window.location.origin + '/docs/oauth2-redirect',
                        presets: [
                          SwaggerUIBundle.presets.apis,
                          SwaggerUIBundle.SwaggerUIStandalonePreset
                        ]
                      })
                    </script>
                    </body>
                    </html>
                  ]]
                  request_handle:respond(
                    {[":status"] = "200", ["content-type"] = "text/html"},
                    html
                  )
                end
              end

```

</details>

2. PersistentVolume and PVC for Static Files
   Provisioned a PersistentVolume backed by a hostPath and a matching PVC to make static assets (Swagger files) available to the pod.

<details> <summary>pvc.yaml</summary>

```
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: swagger-ui-pvc
  namespace: hyperplane-litellm
spec:
  accessModes:
    - ReadOnlyMany
  resources:
    requests:
      storage: 1Gi
  volumeName: swagger-ui-pv
  storageClassName: ""
```

</details>

<details> <summary>pv.yaml</summary>
```
apiVersion: v1
kind: PersistentVolume
metadata:
  name: swagger-ui-pv
spec:
  capacity:
    storage: 1Gi
  accessModes:
    - ReadOnlyMany
  hostPath:
    path: /mnt/static/swagger-ui
  persistentVolumeReclaimPolicy: Retain
```

</details>

3. Deployment: BusyBox HTTP Server Serving the Static Files
   Deployed a lightweight HTTP server (BusyBox httpd) to serve the Swagger UI files from the mounted PVC.

<details> <summary>deployment.yaml + service.yaml</summary>

```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: swagger-static
  namespace: hyperplane-litellm
spec:
  replicas: 1
  selector:
    matchLabels:
      app: swagger-static
  template:
    metadata:
      labels:
        app: swagger-static
    spec:
      nodeSelector:
        hyperplane.dev/nodeType: hyperplane-stack-component-pool-10
      containers:
        - name: busybox-httpd
          image: docker.io/rancher/mirrored-library-busybox:1.36.1
          command: ["httpd", "-f", "-p", "80", "-h", "/usr/share/nginx/html"]
          ports:
            - containerPort: 80
          volumeMounts:
            - name: static-files
              mountPath: /usr/share/nginx/html
              readOnly: true
      volumes:
        - name: static-files
          persistentVolumeClaim:
            claimName: swagger-ui-pvc

apiVersion: v1
kind: Service
metadata:
  name: swagger-static
  namespace: hyperplane-litellm
spec:
  selector:
    app: swagger-static
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
```

</details>

4. Updated a virtualservice.yaml in the helm templates

<details> <summary>virtualservice.yaml</summary>

```
{{- $configmapObject := (lookup "v1" "ConfigMap" "hyperplane-core" "hyperplane-settings") | default dict }}
{{- $cmData := (get $configmapObject "data") | default dict }}
{{- $domainName := (get $cmData "HYPERPLANE_DOMAIN") }}
{{- $istioGateway := (get $cmData "ISTIO_GATEWAY") }}
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: {{ include "litellm.fullname" . }}-vs
  namespace: {{ .Release.Namespace }}
  labels:
    app: {{ include "litellm.fullname" . }}
    release: {{ .Release.Name }}
    hyperplane.dev/stack-component: {{ include "litellm.fullname" . }}
    hyperplane-service-name: "{{ include "litellm.fullname" . }}"
spec:
  gateways:
  - {{ $istioGateway }}
  hosts:
  - "{{ .Release.Name }}.{{ $domainName }}"
  http:
  - match:
    - uri:
        prefix: /swagger-ui.css
    route:
    - destination:
        host: swagger-static.hyperplane-litellm.svc.cluster.local
        port:
          number: 80
  - match:
    - uri:
        prefix: /swagger-ui-bundle.js
    route:
    - destination:
        host: swagger-static.hyperplane-litellm.svc.cluster.local
        port:
          number: 80
  - match:
    - uri:
        prefix: "/"
    route:
    - destination:
        host: {{ include "litellm.fullname" . }}
        port:
          number: 4000
```

</details>
