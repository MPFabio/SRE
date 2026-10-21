# Deploiement Kubernetes

Chart Helm deployant un lab complet par apprenant, un namespace chacun.

## Tester en local avec kind

Prerequis : `kind`, `kubectl`, `helm`.

### 1. Creer le cluster

```bash
kind create cluster --name sre-lab
```

### 2. Construire les images

```bash
for svc in api-gateway catalog-service cart-service orders-service \
           payment-service users-service; do
  docker build --tag $svc:lab --file microservices/$svc/Dockerfile microservices/
done

docker build --tag lab-controller:lab lab-controller/api/
docker build --tag traffic-generator:lab traffic-generator/
```

Si la stack tourne deja en compose, les images existent sous le prefixe
`sre-` : `docker tag sre-api-gateway:latest api-gateway:lab`, et ainsi de
suite pour les huit.

### 3. Charger les images dans le cluster

kind n'a pas acces au demon Docker local : les images doivent y etre
injectees.

```bash
kind load docker-image --name sre-lab \
  api-gateway:lab catalog-service:lab cart-service:lab \
  orders-service:lab payment-service:lab users-service:lab \
  lab-controller:lab traffic-generator:lab
```

### 4. Deployer

```bash
helm install apprenant1 helm/reskilling-lab \
  --namespace apprenant1 --create-namespace \
  --set image.tag=lab \
  --set ingress.enabled=false \
  --set postgres.password=$(openssl rand -hex 24) \
  --set jwtSecret=$(openssl rand -hex 32) \
  --set grafana.adminPassword=$(openssl rand -hex 8) \
  --wait --timeout 5m
```

`ingress.enabled=false` car kind n'a pas de controleur Ingress par defaut.
Les trois secrets sont obligatoires, voir [Secrets](#secrets).

### 5. Verifier

```bash
kubectl get pods --namespace apprenant1
```

Les vingt pods doivent etre `Running`.

```bash
kubectl port-forward --namespace apprenant1 svc/api-gateway 8080:8080 &
kubectl port-forward --namespace apprenant1 svc/lab-controller 8090:8090 &
kubectl port-forward --namespace apprenant1 svc/grafana 3000:3000 &
kubectl port-forward --namespace apprenant1 svc/prometheus 9090:9090 &
```

| Interface | URL |
|---|---|
| Boutique | http://localhost:8080 |
| Operations Console | http://localhost:8090 |
| Grafana | http://localhost:3000 (admin, mot de passe : voir [Secrets](#secrets)) |
| Prometheus | http://localhost:9090 |

Parcours d'achat complet :

```bash
curl --silent --request POST http://localhost:8080/api/cart/test/items \
  --header 'Content-Type: application/json' \
  --data '{"product_id": 1, "quantity": 1}'

curl --silent --request POST http://localhost:8080/api/orders \
  --header 'Content-Type: application/json' \
  --data '{"user_id": "test", "items": [{"product_id": 1, "quantity": 1}],
           "shipping_address": {"street": "1 rue de Rivoli", "city": "Paris",
                                "postal_code": "75001", "country": "FR"}}'
```

Cibles Prometheus, vingt attendues :

```bash
curl --silent http://localhost:9090/api/v1/targets \
  | jq '[.data.activeTargets[] | select(.health == "up")] | length'
```

### 6. Tester l'isolation entre apprenants

```bash
helm install apprenant2 helm/reskilling-lab \
  --namespace apprenant2 --create-namespace \
  --set image.tag=lab --set ingress.enabled=false \
  --set postgres.password=$(openssl rand -hex 24) \
  --set jwtSecret=$(openssl rand -hex 32) \
  --set grafana.adminPassword=$(openssl rand -hex 8) \
  --wait
```

Le chaos injecte chez l'un ne doit pas atteindre l'autre :

```bash
kubectl port-forward --namespace apprenant1 svc/payment-service 8084:8084 &
kubectl port-forward --namespace apprenant2 svc/payment-service 8085:8084 &

curl --silent --request POST http://localhost:8084/api/chaos \
  --header 'Content-Type: application/json' \
  --data '{"enabled": true, "error_rate": 0.8}'

curl --silent http://localhost:8085/api/chaos
```

Le second doit repondre `"enabled": false`.

### 7. Nettoyer

```bash
kind delete cluster --name sre-lab
```

## Construire et pousser les images

```bash
REGISTRY=<compte>.dkr.ecr.<region>.amazonaws.com
TAG=1.0.0

for svc in api-gateway catalog-service cart-service orders-service \
           payment-service users-service; do
  docker build --tag $REGISTRY/$svc:$TAG \
    --file microservices/$svc/Dockerfile microservices/
  docker push $REGISTRY/$svc:$TAG
done

docker build --tag $REGISTRY/lab-controller:$TAG lab-controller/api/
docker build --tag $REGISTRY/traffic-generator:$TAG traffic-generator/
docker push $REGISTRY/lab-controller:$TAG
docker push $REGISTRY/traffic-generator:$TAG
```

## Droits necessaires

Le chart s'installe avec le seul role `edit` dans le namespace : il ne cree
ni Role ni RoleBinding. Promtail lit directement les fichiers de logs du
namespace dans `/var/log/pods`, sans interroger l'API Kubernetes.

## Secrets

Le chart ne contient aucun mot de passe par defaut. `helm install` echoue
tant que les trois valeurs suivantes ne sont pas fournies :

| Valeur | Role |
|---|---|
| `postgres.password` | Mot de passe PostgreSQL |
| `jwtSecret` | Signature des tokens de connexion |
| `grafana.adminPassword` | Mot de passe du compte `admin` de Grafana |

Elles sont stockees dans le Secret `lab-secrets` du namespace. Pour
retrouver le mot de passe Grafana d'un apprenant :

```bash
kubectl get secret lab-secrets --namespace apprenant1 \
  --output jsonpath='{.data.GRAFANA_ADMIN_PASSWORD}' | base64 --decode
```

Pour une mise a jour, `helm upgrade --reuse-values` conserve les secrets
deja poses.

## Deployer un apprenant

```bash
helm install apprenant1 helm/reskilling-lab \
  --namespace apprenant1 --create-namespace \
  --set image.registry=$REGISTRY \
  --set image.tag=$TAG \
  --set ingress.host=apprenant1.lab.exemple.fr \
  --set postgres.password=$(openssl rand -hex 24) \
  --set jwtSecret=$(openssl rand -hex 32) \
  --set grafana.adminPassword=$(openssl rand -hex 8)
```

## Deployer une promotion

```bash
for i in $(seq 1 12); do
  GRAFANA_PASSWORD=$(openssl rand -hex 8)
  helm install apprenant$i helm/reskilling-lab \
    --namespace apprenant$i --create-namespace \
    --set image.registry=$REGISTRY \
    --set image.tag=$TAG \
    --set ingress.host=apprenant$i.lab.exemple.fr \
    --set postgres.password=$(openssl rand -hex 24) \
    --set jwtSecret=$(openssl rand -hex 32) \
    --set grafana.adminPassword=$GRAFANA_PASSWORD
  echo "apprenant$i;$GRAFANA_PASSWORD" >> "$HOME/acces-grafana.csv"
done
```

`$HOME/acces-grafana.csv` contient les mots de passe a remettre a chaque
apprenant : il reste hors du depot.

## Acces

Une seule entree par apprenant, via l'Ingress :

| Chemin | Service |
|---|---|
| `/` | Boutique CapShop |
| `/ops` | Operations Console |
| `/grafana` | Grafana |
| `/prometheus` | Prometheus |
| `/alertmanager` | Alertmanager |
| `/locust` | Generateur de trafic |

Sans Ingress (`--set ingress.enabled=false`) :

```bash
kubectl port-forward --namespace apprenant1 svc/api-gateway 8080:8080
```

## Dimensionnement

Requests par apprenant : 1,7 Go de memoire, 0,41 vCPU.

| Type de noeud | Apprenants |
|---|---|
| t3a.xlarge (16 Go / 4 vCPU) | 7 |
| t3a.2xlarge (32 Go / 8 vCPU) | 15 |
| m6a.4xlarge (64 Go / 16 vCPU) | 31 |

## Isolation entre apprenants

Le namespace seul n'isole rien : sans regle, un apprenant joint le PostgreSQL
d'un autre par `postgres.apprenant2.svc.cluster.local` et peut consommer toute
la memoire du noeud. Trois mecanismes ferment ces acces. Seule la
NetworkPolicy est active par defaut : un stagiaire avec le role `edit` n'a
pas le droit de creer de ResourceQuota ni de LimitRange.

### NetworkPolicy

Trafic autorise uniquement a l'interieur du namespace, plus le DNS vers
kube-system et l'entree depuis le controleur d'Ingress. Tout le reste est
refuse, dans les deux sens.

```yaml
isolation:
  networkPolicy:
    enabled: true
    ingressNamespace: ingress-nginx     # namespace du controleur
    extraIngressNamespaces: []          # ex: monitoring central
    allowExternalEgress: false          # sortie Internet
```

Le CNI doit appliquer les NetworkPolicy. C'est le cas de Calico et Cilium,
donc de l'add-on VPC CNI d'EKS avec l'application des politiques activee.
Ce n'est pas le cas de kindnet, le CNI par defaut de kind : les politiques y
sont acceptees mais ignorees.

### ResourceQuota

Plafonne ce que le namespace consomme au total. Desactive par defaut, a
poser par l'administrateur du cluster, ou avec
`--set isolation.resourceQuota.enabled=true` si l'installation se fait avec
un compte qui en a le droit.

```yaml
  resourceQuota:
    requestsMemory: 3Gi
    limitsMemory: 8Gi
    requestsCpu: "1"
    limitsCpu: "18"
    pods: 30
    pvcs: 4
```

Les valeurs couvrent la stack avec une marge : la somme des limites des vingt
conteneurs atteint 6,1 Gi et 14,5 vCPU. `services.loadbalancers` et
`services.nodeports` sont a zero, pour qu'un apprenant ne puisse pas exposer
un service hors du cluster.

### LimitRange

Borne chaque conteneur pris isolement et donne des valeurs par defaut aux pods
qui n'en declarent pas. Desactive par defaut, pour la meme raison que la
ResourceQuota : `--set isolation.limitRange.enabled=true`.

```yaml
  limitRange:
    defaultRequestMemory: 64Mi
    defaultMemory: 256Mi
    maxMemory: 1Gi
    maxCpu: "2"
```

Un apprenant qui lance `kubectl run` sans preciser de ressources obtient les
valeurs par defaut au lieu d'un pod sans limite.

### Verifier

```bash
kubectl describe resourcequota lab-quota --namespace apprenant1
kubectl get networkpolicy --namespace apprenant1
```

Depuis un pod du namespace, un appel vers un autre namespace doit echouer :

```bash
kubectl run test --namespace apprenant1 --image=curlimages/curl --rm --stdin --tty   -- curl --max-time 5 http://postgres.apprenant2.svc.cluster.local:5432
```

### Ce que cela ne couvre pas

L'isolation porte sur le reseau et les ressources. Pour empecher un apprenant
de lire les namespaces voisins avec `kubectl`, il faut en plus un RBAC
restreignant son compte a son propre namespace, ce qui se gere au niveau du
cluster et non du chart.

## Retention et persistance

Par defaut, Prometheus conserve 15 jours et Loki 7 jours, mais les donnees
vivent dans un `emptyDir` : elles disparaissent si le pod redemarre.
Suffisant pour une session courte.

Pour une session s'etalant sur plusieurs jours, activer les volumes :

```bash
helm install apprenant1 helm/reskilling-lab \
  --namespace apprenant1 --create-namespace \
  --set persistence.prometheus.enabled=true \
  --set persistence.loki.enabled=true \
  --set persistence.tempo.enabled=true \
  --set postgres.password=$(openssl rand -hex 24) \
  --set jwtSecret=$(openssl rand -hex 32) \
  --set grafana.adminPassword=$(openssl rand -hex 8)
```

Trois PVC sont alors crees (5 Gi, 5 Gi, 3 Gi par defaut), a ajuster avec
`persistence.<composant>.size`.

### Cout reel

Mesure sur la stack : 11 700 series actives, 768 echantillons par seconde,
soit **5,4 Mo par heure** de donnees Prometheus.

| Retention | Disque par apprenant |
|---|---|
| 24 h | 130 Mo |
| 3 jours | 390 Mo |
| 7 jours | 900 Mo |
| 15 jours | 1,9 Go |

La memoire de Prometheus ne depend pas de la retention mais du nombre de
series : seules les deux dernieres heures restent en tete, le reste est
sur disque. Mesure a 184 Mo apres 16 h de collecte.

Loki et Tempo suivent le meme principe. Les valeurs de retention se
reglent par `retention.prometheus`, `retention.prometheusSize` et
`retention.loki`.

## Ecarts avec docker-compose

| Sujet | Compose | Kubernetes |
|---|---|---|
| Logs | Promtail lit le socket Docker | DaemonSet, `kubernetes_sd_configs` |
| PostgreSQL | volume nomme | StatefulSet + PVC |
| Prometheus, Loki, Tempo | volumes nommes | `emptyDir`, PVC en option |
| Grafana | volume nomme | `emptyDir` |

## Supprimer

```bash
helm uninstall apprenant1 --namespace apprenant1
kubectl delete namespace apprenant1
```

Le PVC de PostgreSQL survit a `helm uninstall` : supprimer le namespace
libere le volume EBS.
