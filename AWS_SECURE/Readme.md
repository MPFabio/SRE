# Installer le lab SRE dans EKS

Toutes les commandes se lancent sur votre machine `utils-stagiaireXX`, une fois
connecte, ou `kubectl` est deja configure sur votre namespace.

## 1. Enregistrer votre identifiant

Une fois pour toutes : il reste disponible apres une reconnexion et dans chaque
nouveau terminal.

```sh
echo 'export STAGIAIRE=$(whoami)' >> ~/.bashrc
source ~/.bashrc
echo $STAGIAIRE
kubectl auth whoami
```

## 2. Installer les outils

Git :

```sh
sudo dnf install -y git
```

Helm :

```sh
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

Docker :

```sh
sudo dnf install -y docker
sudo systemctl enable --now docker.service
sudo usermod -aG docker $STAGIAIRE
```

Le groupe `docker` n'est pris en compte qu'a la connexion suivante : se
deconnecter (`exit`), se reconnecter, puis verifier :

```sh
docker version
echo $STAGIAIRE
```

`docker version` doit afficher les parties `Client` et `Server`, sans
`permission denied`.

## 3. Recuperer le projet

```sh
git clone https://github.com/MPFabio/SRE.git
cd SRE
```

## 4. Construire et pousser les images

Le push se fait sur `docker-push.reskilling.internal`, dans votre espace :

```sh
docker login docker-push.reskilling.internal -u $STAGIAIRE

export REGISTRY=docker-push.reskilling.internal/$STAGIAIRE

for SVC in api-gateway catalog-service cart-service orders-service payment-service users-service
do
    docker build --tag $REGISTRY/$SVC:lab --file microservices/$SVC/Dockerfile microservices/
done

docker build --tag $REGISTRY/lab-controller:lab lab-controller/api/
docker build --tag $REGISTRY/traffic-generator:lab traffic-generator/

for SVC in api-gateway catalog-service cart-service orders-service payment-service users-service lab-controller traffic-generator
do
    docker push $REGISTRY/$SVC:lab
done
```

## 5. Installer le lab

Le cluster tire les images depuis `docker.reskilling.internal`. Les trois
secrets sont obligatoires.

```sh
helm install lab helm/reskilling-lab \
    --namespace $STAGIAIRE \
    --set image.registry=docker.reskilling.internal/$STAGIAIRE \
    --set image.tag=lab \
    --set postgres.password=$(openssl rand -hex 24) \
    --set jwtSecret=$(openssl rand -hex 32) \
    --set grafana.adminPassword=$(openssl rand -hex 8)
```

Le chart ne cree ni Role, ni RoleBinding, ni quota : il s'installe avec les
droits du namespace.

## 6. Verifier

```sh
kubectl get pods --watch
```

Les vingt pods doivent passer `Running` en quelques minutes.

| Message | Cause, solution |
|---|---|
| `Pending` et `Too many pods` | plus de place sur les noeuds : voir le formateur |
| `ImagePullBackOff` sur une de vos images | image absente du Nexus : refaire l'etape 4 |
| `ImagePullBackOff` sur une image publique (postgres, grafana...) | relancer avec `--set image.publicRegistry=docker.reskilling.internal` |

Pour lire la raison exacte :

```sh
kubectl get events --sort-by=.lastTimestamp | tail -20
```

## 7. Recuperer le mot de passe Grafana

```sh
kubectl get secret lab-secrets \
    --output jsonpath='{.data.GRAFANA_ADMIN_PASSWORD}' | base64 --decode
```

L'identifiant est `admin`.

## 8. Acceder aux interfaces

Sur `utils-stagiaireXX`, ouvrir les ports, et laisser le terminal ouvert :

```sh
kubectl port-forward svc/api-gateway 8080:8080 &
kubectl port-forward svc/lab-controller 8090:8090 &
kubectl port-forward svc/grafana 3000:3000 &
kubectl port-forward svc/prometheus 9090:9090 &
kubectl port-forward svc/alertmanager 9093:9093 &
kubectl port-forward svc/traffic-generator 8089:8089 &
```

Depuis votre poste, un tunnel SSH ramene ces ports, et laisser ce terminal
ouvert aussi :

```sh
ssh -L 8080:localhost:8080 -L 8090:localhost:8090 -L 3000:localhost:3000 \
    -L 9090:localhost:9090 -L 9093:localhost:9093 -L 8089:localhost:8089 \
    utils-stagiaireXX
```

| Interface | Adresse |
|---|---|
| Boutique CapShop | http://localhost:8080 |
| Operations Console | http://localhost:8090 |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| Alertmanager | http://localhost:9093 |
| Locust | http://localhost:8089 |

Ce sont les adresses utilisees dans les exercices.

## 9. Supprimer le lab

```sh
helm uninstall lab --namespace $STAGIAIRE
```
