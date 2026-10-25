{{- define "lab.labels" -}}
app.kubernetes.io/part-of: reskilling-lab
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "lab.databaseUrl" -}}
postgresql://{{ .Values.postgres.user }}:$(POSTGRES_PASSWORD)@postgres:5432/{{ .Values.postgres.database }}
{{- end }}

{{- define "lab.publicImage" -}}
{{- $root := index . 0 -}}
{{- with $root.Values.image.publicRegistry }}{{ . }}/{{ end }}{{ index . 1 }}
{{- end }}

{{- define "lab.image" -}}
{{- if .registry }}{{ .registry }}/{{ end }}{{ .name }}:{{ .tag }}
{{- end }}

{{- define "lab.learner" -}}
{{- $l := .Values.learnerService | default dict -}}
{{- toYaml (dict
  "enabled" ($l.enabled | default false)
  "name" ($l.name | default "reviews-service")
  "image" ($l.image | default "")
  "port" ($l.port | default 8086)
  "replicas" ($l.replicas | default 1)
  "healthPath" ($l.healthPath | default "/health")
  "metricsPath" ($l.metricsPath | default "/metrics")
  "database" ($l.database | default false)
  "imagePullSecret" ($l.imagePullSecret | default "")
  "env" ($l.env | default dict)
  "shop" ($l.shop | default false)) -}}
{{- end }}
