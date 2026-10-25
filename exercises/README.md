# Exercices du parcours - fil rouge

Ces exercices sont ceux de la formation, aux transitions entre modules. Ils
portent tous sur **votre module** : un service que vous ajoutez à CapShop,
dans le langage et sur le métier de votre choix. Un exemple guidé est
fourni à chaque étape ; suivez-le, adaptez-le ou faites autrement.

Chaque exercice se termine par un bloc « Ça bloque ? » et par des critères
de réussite à comparer avec votre résultat. Personne ne doit rester
bloqué : chaque étape du module existe en version prête à l'emploi.

Les exercices facultatifs, pour aller plus loin sur les pratiques SRE,
sont dans le dossier [bonus](bonus/README.md).

## Correspondance avec la formation

### Parcours DevOps SRE (sprint 2)

| Transition | Exercice de la formation | Exercice associé |
|---|---|---|
| Prometheus et Grafana > OpenTelemetry | Métriques business | [P1](#p1--installer-lapplication-fil-rouge), [P2](#p2--écrire-votre-module), [P3](#p3--déployer-votre-module), [P4](#p4--métriques-business) |
| | Dashboard | [P5](#p5--dashboard-de-votre-module) |
| OpenTelemetry > Platform Engineering | Instrumenter avec OpenTelemetry | [P6](#p6--traces-et-étape-la-plus-lente) |
| | Trace et étape la plus lente | [P6](#p6--traces-et-étape-la-plus-lente) |
| Intégration continue > Kubernetes | Pipeline : construire et pousser l'image | [P7](#p7--pipeline--construire-et-pousser-limage) |
| Kubernetes | Déployer le service (stack complète) | [P3](#p3--déployer-votre-module) |
| | Lancer les scripts de chaos | [P8](#p8--chaos--diagnostiquer-et-corriger) |
| | Diagnostiquer et corriger | [P8](#p8--chaos--diagnostiquer-et-corriger) |

Votre service FastAPI devient ici un module de CapShop. L'application fil rouge est
nécessaire dès les métriques, pour les voir dans Prometheus et Grafana : le
déploiement (P1 et P3) arrive donc avant le module Kubernetes, qui le
reprend ensuite.

### Parcours DevOps Infra (sprint 2)

| Transition | Exercice de la formation | Exercice associé |
|---|---|---|
| Golang + Kubernetes > Platform Engineering | Développer un module en Go | [P2](#p2--écrire-votre-module) |
| | Le déployer dans Kubernetes (stack complète) | [P1](#p1--installer-lapplication-fil-rouge), [P3](#p3--déployer-votre-module) |
| Fin du module Prometheus et Grafana | Métriques business | [P4](#p4--métriques-business) |
| | Dashboard | [P5](#p5--dashboard-de-votre-module) |
| Fin du sprint 2 | Lancer les scripts de chaos | [P8](#p8--chaos--diagnostiquer-et-corriger) |
| | Corriger les problèmes provoqués | [P8](#p8--chaos--diagnostiquer-et-corriger) |

---

## P1 : Installer l'application fil rouge

**Objectif** : CapShop et sa stack d'observabilité tournent dans votre
namespace.

Suivez [Installer l'application fil rouge dans EKS](../AWS_SECURE/README.md), étapes 1 à 8 :
construction des images, `helm install`, accès aux interfaces.

<details>
<summary>Critères de réussite</summary>

- `kubectl get pods` : tous les pods sont `Running` et prêts.
- La boutique s'ouvre sur http://localhost:8080 et un achat aboutit.
- Grafana (http://localhost:3000) affiche le dashboard *SRE Overview*.

</details>

Dépannage : tableau de l'étape 6 de l'installation.

---

## P2 : Écrire votre module

**Objectif** : un service HTTP qui rend un service métier à CapShop, avec
un endpoint `/health`, construit en image Docker.

1. Choisissez un métier : avis produits (l'exemple), estimation de
   livraison, programme de fidélité, recommandations, liste d'envies...
2. Suivez l'étape 1 du guide de votre langage :
   [Go](../fil-rouge/module-go.md#étape-1--une-api-et-un-endpoint-health)
   ou [Python](../fil-rouge/module-python.md#étape-1--une-api-et-un-endpoint-health).
3. Testez-le sur `utils-stagiaireXX` avec `docker run` et `curl`.

Le module doit respecter quatre conditions pour s'intégrer à l'application fil rouge : image
Docker, port lu dans `PORT`, endpoint de health check, logs sur stdout.
Voir [les conditions](../fil-rouge/README.md#conditions-pour-sintégrer-à-lapplication-fil-rouge).

<details>
<summary>Ça bloque ?</summary>

Chaque guide a son tableau de dépannage à la fin de l'étape 1. Si vous
manquez de temps, construisez la version prête à l'emploi
([Go](../fil-rouge/reviews-service/go/1-base/) ou [Python](../fil-rouge/reviews-service/python/1-base/)) et passez à P3 :
vous reprendrez votre propre code plus tard.

</details>

<details>
<summary>Critères de réussite</summary>

- `curl localhost:8086/health` répond 200.
- Votre route métier répond, et refuse proprement une entrée invalide
  (4xx, pas 500).
- `docker logs` montre une ligne de log par action métier.

</details>

---

## P3 : Déployer votre module

**Objectif** : votre module tourne dans l'application fil rouge, à côté des six services, et
la stack le voit.

1. Poussez l'image sur le registry GitLab de votre projet, autorisez le
   cluster à le lire, puis activez le module dans le chart :
   [Déployer votre module](../fil-rouge/README.md#déployer-votre-module).
2. Rechargez Prometheus pour qu'il prenne en compte la nouvelle target.
3. Vérifiez avec la section [Vérifier](../fil-rouge/README.md#vérifier).

<details>
<summary>Ça bloque ?</summary>

Tableau « Ça bloque ? » du [module fil rouge](../fil-rouge/README.md#vérifier) :
image introuvable, pod qui redémarre, pod jamais prêt, target absente de
Prometheus.

</details>

<details>
<summary>Critères de réussite</summary>

- `kubectl get pods -l app=<votre module>` : `1/1 Running`.
- `kubectl exec deploy/api-gateway -- curl --silent <module>:8086/health`
  répond, depuis l'intérieur du cluster.
- Grafana, Explore, Loki : `{job="<votre module>"}` affiche vos logs.
- Prometheus, *Targets* : la probe `blackbox-<module>` est `up`. La target
  `<module>` est `down` tant que `/metrics` n'existe pas : c'est P4.

</details>

---

## P4 : Métriques business

**Objectif** : votre module expose des métriques qui répondent à des
questions du métier, et Prometheus les collecte.

1. Listez trois ou quatre questions qu'un responsable métier se poserait
   sur votre service.
2. Pour chaque question, choisissez une métrique et son type (Counter,
   Gauge, Histogram) et ses labels.
3. Implémentez-les et exposez `/metrics` : étape 2 du guide
   ([Go](../fil-rouge/module-go.md#étape-2--des-métriques-business),
   [Python](../fil-rouge/module-python.md#étape-2--des-métriques-business)).
4. Redéployez (P3, avec un nouveau tag) et vérifiez dans Prometheus.

<details>
<summary>Ça bloque ?</summary>

- Tableau de dépannage de l'étape 2 du guide.
- La métrique existe mais reste à zéro : votre module ne reçoit pas de
  trafic. Appelez-le vous-même, ou lancez `bash fil-rouge/trafic.sh`
  (prévu pour l'exemple d'avis ; adaptez-le à vos routes).
- Version prête à l'emploi : [Go](../fil-rouge/reviews-service/go/2-metriques/) ou [Python](../fil-rouge/reviews-service/python/2-metriques/).

</details>

<details>
<summary>Exemple (module d'avis)</summary>

| Question métier | Métrique | Type |
|---|---|---|
| Combien d'avis publie-t-on ? | `reviews_created_total{rating}` | Counter |
| Combien en refuse-t-on, et pourquoi ? | `reviews_rejected_total{reason}` | Counter |
| Les clients sont-ils satisfaits ? | `reviews_average_rating{product_id}` | Gauge |

</details>

<details>
<summary>Critères de réussite</summary>

- La target de votre module est `up` dans http://localhost:9090/targets.
- Chaque métrique business répond dans Prometheus, par exemple
  `sum by (rating) (reviews_created_total)`.
- Chaque métrique a un nom explicite, une unité claire (`_total`,
  `_seconds`) et des labels à faible cardinalité : pas d'identifiant
  d'utilisateur ni de commentaire en label.
- Vous savez dire à quelle question métier répond chaque métrique.

</details>

---

## P5 : Dashboard de votre module

**Objectif** : un dashboard Grafana qui raconte l'état de votre service à
quelqu'un qui ne connaît pas son code.

1. Générez du trafic (`bash fil-rouge/trafic.sh` pour l'exemple, ou vos
   propres appels) et laissez-le tourner.
2. Créez un dashboard : Grafana, **Dashboards**, **New**, **New dashboard**,
   puis **Add visualization**. La marche à suivre détaillée (source,
   éditeur Code, unités, seuils) est dans le
   [guide Grafana](../docs/OBSERVABILITY.md#modifier-le-dashboard).
3. Prévoyez au moins :
   - un panel par question métier de P4 ;
   - le trafic et le taux d'erreur de votre service ;
   - la latence (P95 ou P99) ;
   - les logs récents de votre module (source Loki).

<details>
<summary>Ça bloque ?</summary>

- **« No data »** : vérifiez la période en haut à droite, et que la requête
  répond dans Prometheus d'abord.
- **Courbe plate à zéro** : pas de trafic récent, relancez
  `fil-rouge/trafic.sh`.
- **Un Counter affiché tel quel** monte sans fin : affichez son rythme avec
  `rate(...[5m])`.
- **Trop de courbes** : regroupez avec `sum by (label)`.

</details>

<details>
<summary>Exemple de requêtes (module d'avis)</summary>

| Panel | Visualisation | Requête |
|---|---|---|
| Avis publiés par minute, par note | Time series | `sum by (rating) (rate(reviews_created_total[5m])) * 60` |
| Part des avis refusés | Stat ou Gauge, unité *Percent (0.0-1.0)* | `sum(rate(reviews_rejected_total[5m])) / (sum(rate(reviews_created_total[5m])) + sum(rate(reviews_rejected_total[5m])))` |
| Motifs de refus | Pie chart ou Bar chart | `sum by (reason) (rate(reviews_rejected_total[5m])) * 60` |
| Produits les mieux notés | Bar gauge | `topk(5, reviews_average_rating)` |
| Requêtes par code HTTP | Time series | `sum by (status) (rate(http_requests_total{job="reviews-service"}[5m]))` |
| Latence P95 | Time series, unité *seconds* | `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="reviews-service"}[5m])))` |
| Logs | Logs, source Loki | `{job="reviews-service"} != "/health"` |

Avec le trafic de `trafic.sh`, une part importante des avis est refusée :
le script envoie volontairement des mots interdits (environ 30 % de refus
à l'étape 2), puis des produits inconnus, refusés à partir de l'étape 3
qui vérifie chaque produit auprès du catalogue (environ 40 % au total).

</details>

<details>
<summary>Critères de réussite</summary>

- Le dashboard se lit sans connaître le code : titres en langage métier,
  unités renseignées.
- Le haut du dashboard répond à « le service va-t-il bien ? » (trafic,
  erreurs, latence) ; le bas détaille le métier.
- Pendant une panne (P8), le dashboard le montre.

</details>

---

## P6 : Traces et étape la plus lente

**Objectif** : votre module envoie des traces à Tempo, et vous savez lire
où passe le temps d'une requête.

1. Instrumentez votre module : étape 3 du guide
   ([Go](../fil-rouge/module-go.md#étape-3--des-traces-opentelemetry),
   [Python](../fil-rouge/module-python.md#étape-3--des-traces-opentelemetry)).
   Découpez le traitement en spans, un par étape métier.
2. Redéployez, générez du trafic.
3. Grafana, Explore, source **Tempo**, onglet TraceQL :

   ```traceql
   { resource.service.name = "reviews-service" }
   ```

4. Ouvrez une trace de création et identifiez l'étape la plus lente.
   Comparez plusieurs traces : est-ce toujours la même ?

<details>
<summary>Ça bloque ?</summary>

- Tableau de dépannage de l'étape 3 du guide.
- Pour comparer les traces, triez les résultats sur la colonne **Duration**.
  Une création d'avis prend quelques millisecondes : pour ne garder que les
  plus lentes, ajustez le seuil à ce que vous observez, par exemple
  `{ resource.service.name = "reviews-service" && duration > 5ms }`.
- Version prête à l'emploi : [Go](../fil-rouge/reviews-service/go/3-traces/) ou [Python](../fil-rouge/reviews-service/python/3-traces/).

</details>

<details>
<summary>Réponse (module d'avis)</summary>

Une trace de `POST /api/reviews/{product_id}` contient :

| Span | Service | Durée typique |
|---|---|---|
| `POST /api/reviews/{product_id}` | reviews-service | quelques ms |
| `verify_product` | reviews-service | presque toute la durée |
| `GET /api/products/{product_id}` | catalog-service | dans `verify_product` |
| `moderate_review`, `store_review` | reviews-service | quelques µs |

L'étape la plus lente est `verify_product` : c'est le seul appel réseau, et
il attend la réponse du catalogue, qui lui-même interroge PostgreSQL. Le
traitement local (modération, stockage en mémoire) est négligeable.

C'est le cas général : dans un service, le temps part presque toujours dans
les appels aux dépendances (réseau, base, autres services). Si
`catalog-service` n'apparaît pas dans la trace, le contexte n'est pas
propagé : voir le tableau de dépannage.

</details>

---

## P7 : Pipeline : construire et pousser l'image

**Objectif** : le pipeline GitLab de votre projet construit l'image de votre
module et la pousse sur le registry du GitLab commun, à chaque push. Vous
déployez ensuite l'application fil rouge à partir de cette image.

1. Ajoutez à votre projet le pipeline d'exemple, ou complétez le vôtre :
   [pipeline de construction d'image](../fil-rouge/ci/README.md).
2. Poussez un commit et suivez le job dans **Build** → **Pipelines**.
3. Vérifiez la nouvelle image dans **Deploy** → **Container Registry** : un
   tag par commit, plus `latest`.
4. Déployez cette image :

   ```bash
   helm upgrade lab helm/reskilling-lab --namespace $STAGIAIRE --reuse-values \
       --set learnerService.image=$IMAGE:<tag du commit>
   ```

<details>
<summary>Ça bloque ?</summary>

Tableau « Ça bloque ? » du [pipeline de construction d'image](../fil-rouge/ci/README.md).

</details>

<details>
<summary>Critères de réussite</summary>

- Un push sur la branche par défaut déclenche le pipeline, qui passe au vert.
- Le registry contient une image par commit : vous savez quel code tourne.
- Le module déployé avec ce tag répond (`/health`), sans `docker build` sur
  votre VM.
- Vous savez expliquer pourquoi déployer un tag de commit plutôt que
  `latest`.

</details>

<details>
<summary>Réponse : pourquoi un tag de commit ?</summary>

`latest` change de contenu à chaque push : le même nom désigne des images
différentes d'un jour à l'autre, et Kubernetes peut garder une ancienne
version en cache. Un tag par commit est immuable : on sait exactement quel
code tourne, et revenir en arrière consiste à redéployer le tag précédent.

</details>

---

## P8 : Chaos : diagnostiquer et corriger

**Objectif** : face à une vraie panne, trouver la cause avec vos outils
d'observabilité, la corriger et mesurer le temps que cela a pris.

1. Lancez une panne au hasard sur votre module :

   ```bash
   bash chaos/inject.sh "" <votre module>
   ```

   ou sans argument pour l'exemple `reviews-service`. Notez l'heure.
2. Diagnostiquez **en partant de vos dashboards et de vos traces**, puis
   des alertes et de `kubectl`. Démarche détaillée :
   [scripts de chaos](../chaos/README.md#diagnostiquer). Si les avis sont
   affichés dans la boutique (`learnerService.shop`), regardez aussi ce
   que voit un client.
3. Corrigez avec `kubectl`, vérifiez le retour à la normale, puis lancez
   `bash chaos/rollback.sh` pour nettoyer.
4. Recommencez avec d'autres scénarios, dont `base` et `cache`, qui
   touchent CapShop plutôt que votre module.

Pour chaque panne, notez l'heure de la panne, de la première alerte, du
diagnostic et du retour à la normale.

<details>
<summary>Ça bloque ?</summary>

- Pistes par scénario dans [chaos/README.md](../chaos/README.md#pistes-et-solutions),
  séparées des solutions.
- `bash chaos/rollback.sh` remet le service en l'état d'avant la panne.

</details>

<details>
<summary>Critères de réussite</summary>

- Pour chaque panne, vous savez dire **ce que vous avez vu en premier**
  (alerte, dashboard, trace) et **ce qui vous a donné la cause** (souvent
  `kubectl describe pod` ou les logs).
- Votre correction rétablit le service sans `rollback.sh`.
- Délai de détection et MTTR calculés pour chaque panne.
- Une idée par panne pour la détecter plus vite ou l'éviter : alerte sur le
  nombre de redémarrages, vérification de l'image dans le pipeline, limites
  mémoire mesurées plutôt que devinées...

</details>
