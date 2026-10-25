# Installer l'application fil rouge dans EKS

Toutes les commandes se lancent sur votre machine `utils-stagiaireXX`, une fois
connecté, où `kubectl` est déjà configuré sur votre namespace.

## 1. Enregistrer votre identifiant

Une fois pour toutes : il reste disponible après une reconnexion et dans chaque
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

Le groupe `docker` n'est pris en compte qu'à la connexion suivante : se
déconnecter (`exit`), se reconnecter, puis vérifier :

```sh
docker version
echo $STAGIAIRE
```

`docker version` doit afficher les parties `Client` et `Server`, sans
`permission denied`.

## 3. Récupérer le projet

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

Un build peut échouer sur une erreur réseau passagère (`pip install`,
`apt-get`), et le push de cette image échoue ensuite avec `An image does
not exist locally`. Relancez alors tout le bloc : les images déjà
construites et poussées passent en quelques secondes.

## 5. Installer l'application fil rouge

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

Le chart ne crée ni Role, ni RoleBinding, ni quota : il s'installe avec les
droits du namespace.

## 6. Vérifier

```sh
kubectl get pods --watch
```

Tous les pods doivent passer `Running` et `1/1` en quelques minutes : une
vingtaine, dont un `promtail` par nœud du cluster. Un redémarrage au
démarrage des services qui utilisent la base (catalog, orders, users, la
console) est normal : ils attendent que PostgreSQL soit prêt.

| Message | Cause, solution |
|---|---|
| `ImagePullBackOff` sur une de vos images | image absente du Nexus : refaire l'étape 4 |
| `ImagePullBackOff` sur une image publique (postgres, grafana...) | passer par le proxy du Nexus : `helm upgrade lab helm/reskilling-lab --namespace $STAGIAIRE --reuse-values --set image.publicRegistry=docker.reskilling.internal` |

Pour lire la raison exacte :

```sh
kubectl get events --sort-by=.lastTimestamp | tail -20
```

## 7. Récupérer le mot de passe Grafana

```sh
kubectl get secret lab-secrets \
    --output jsonpath='{.data.GRAFANA_ADMIN_PASSWORD}' | base64 --decode
```

L'identifiant est `admin`.

## 8. Accéder aux interfaces

Les interfaces tournent dans le cluster. Deux façons de les ouvrir depuis le
navigateur de votre poste, au choix :

| | A. Tunnel SSH | B. Proxy SOCKS avec FoxyProxy |
|---|---|---|
| Sur votre poste | un terminal ouvert | un terminal ouvert + l'extension FoxyProxy dans Chrome |
| Adresses | `http://localhost:8080`... | `http://<nom de la VM>:8080`... |
| Ports ouverts sur le réseau | aucun | les six ports de la VM, visibles du réseau de la plateforme |

Les exercices écrivent les adresses en `http://localhost:...`. Avec
l'option B, remplacez `localhost` par le nom de la VM dans le navigateur. Les
commandes `curl localhost:...` lancées sur `utils-stagiaireXX` fonctionnent
dans les deux cas.

### Option A : tunnel SSH

Sur `utils-stagiaireXX`, ouvrir les ports en arrière-plan. Ils restent actifs
après la déconnexion :

```sh
for svc in api-gateway:8080 lab-controller:8090 grafana:3000 prometheus:9090 alertmanager:9093 traffic-generator:8089; do
  nohup kubectl port-forward svc/${svc%%:*} ${svc##*:}:${svc##*:} > /dev/null 2>&1 &
done
```

Vérifier que les six ports écoutent :

```sh
ss -ltnp | grep kubectl
```

Depuis votre poste, ouvrir un tunnel SSH vers la machine, et laisser ce
terminal ouvert :

```sh
ssh -L 8080:localhost:8080 -L 8090:localhost:8090 -L 3000:localhost:3000 -L 9090:localhost:9090 -L 9093:localhost:9093 -L 8089:localhost:8089 utils-stagiaireXX
```

Aucun réglage du navigateur n'est nécessaire.

### Option B : proxy SOCKS avec FoxyProxy (Chrome)

Sur `utils-stagiaireXX`, ouvrir les ports en arrière-plan, sur toutes les
interfaces de la machine (`--address 0.0.0.0`), puis noter le nom de la
machine :

```sh
for svc in api-gateway:8080 lab-controller:8090 grafana:3000 prometheus:9090 alertmanager:9093 traffic-generator:8089; do
  nohup kubectl port-forward --address 0.0.0.0 svc/${svc%%:*} ${svc##*:}:${svc##*:} > /dev/null 2>&1 &
done
ss -ltnp | grep kubectl     # six lignes en 0.0.0.0
hostname
```

Depuis votre poste, ouvrir le proxy SOCKS, et laisser ce terminal ouvert
(il n'affiche rien, c'est normal) :

```sh
ssh -D 1080 -N utils-stagiaireXX
```

Dans Chrome, installer l'extension **FoxyProxy Standard**, puis :

1. Icône FoxyProxy, **Options**, onglet **Proxies**, **Add**
2. Type **SOCKS5**, Hostname `127.0.0.1`, Port `1080`, titre `reskilling`, **Save**
3. Icône FoxyProxy : sélectionner **reskilling**

Chrome fait résoudre les noms par la VM à travers le proxy SOCKS5 : les noms
internes de la plateforme fonctionnent. Ouvrir ensuite
`http://<nom de la VM>:8080`. Chrome ne fait jamais passer `localhost` par un
proxy : utilisez bien le nom de la VM.

Après la session, repasser FoxyProxy sur **Disable**, sinon la navigation échoue
dès que le tunnel est fermé.

### Adresses

| Interface | Option A | Option B |
|---|---|---|
| Boutique CapShop | `http://localhost:8080` | `http://<nom de la VM>:8080` |
| Operations Console | `http://localhost:8090` | `http://<nom de la VM>:8090` |
| Grafana | `http://localhost:3000` | `http://<nom de la VM>:3000` |
| Prometheus | `http://localhost:9090` | `http://<nom de la VM>:9090` |
| Alertmanager | `http://localhost:9093` | `http://<nom de la VM>:9093` |
| Locust | `http://localhost:8089` | `http://<nom de la VM>:8089` |

### Relancer les ports

Un port-forward vise un pod précis : si le pod redémarre, l'interface ne répond
plus. Sur `utils-stagiaireXX`, arrêter les ports :

```sh
pkill -f "kubectl port-forward"
```

puis relancer la boucle de votre option. Le tunnel ou le proxy sur votre poste
n'a pas besoin d'être relancé.

| Symptôme | Cause probable | Solution |
|---|---|---|
| La page ne répond plus après un redémarrage de pod | Port-forward tombé avec l'ancien pod | Relancer les ports, ci-dessus |
| Option B : `ERR_PROXY_CONNECTION_FAILED` | Le terminal `ssh -D` est fermé | Relancer `ssh -D 1080 -N utils-stagiaireXX` |
| Option B : "adresse IP introuvable" | Proxy configuré en SOCKS4, ou FoxyProxy désactivé | Type SOCKS5, et **reskilling** sélectionné |
| Option B : `localhost` ne répond pas | Chrome ne passe pas `localhost` par le proxy | Utiliser le nom de la VM |
| Option B : le nom répond mais la page reste vide | Ports ouverts sans `--address 0.0.0.0` | `pkill`, puis relancer la boucle de l'option B |

## 9. Récupérer une correction de l'application fil rouge

Quand une correction de l'application fil rouge est publiée sur le repo,
récupérer le code, puis refaire l'étape 4 (construire et pousser les images) avec le même tag `lab`.
Appliquer ensuite le chart à jour, puis redémarrer les services, qui
téléchargent la nouvelle version :

```sh
git pull
# ... étape 4 ...
helm upgrade lab helm/reskilling-lab --namespace $STAGIAIRE --reuse-values
kubectl rollout restart deployment api-gateway catalog-service cart-service \
    orders-service payment-service users-service lab-controller traffic-generator
kubectl get pods --watch
```

Relancer enfin les ports de l'étape 8 : ils sont tombés avec les anciens pods.

Si la correction touche les règles d'alerte, rechargez Prometheus une
minute après le `helm upgrade` :

```sh
curl --request POST http://localhost:9090/-/reload
```

Si elle touche Grafana (dashboard, sources de données), redémarrez-le :
`kubectl rollout restart deployment grafana`.

Pour mettre à jour votre propre module, voir le guide de votre langage dans
[fil-rouge/](../fil-rouge/README.md).

## 10. Supprimer l'application fil rouge

```sh
helm uninstall lab --namespace $STAGIAIRE
```

Le secret `gitlab-registry`, créé à la main pour votre module, reste en
place : `kubectl delete secret gitlab-registry` le supprime.
