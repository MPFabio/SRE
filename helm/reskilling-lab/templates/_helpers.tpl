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
