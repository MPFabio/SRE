# Exercices bonus - fil rouge

> Les exercices de la formation, sur votre module fil rouge, sont dans
> [les exercices du parcours](../README.md).

## Exercices bonus

Ces exercices sont **facultatifs** : ils ne font pas partie du parcours de
formation. Ils s'adressent à ceux qui veulent aller plus loin sur les
pratiques SRE. Faites ceux qui vous intéressent, à votre rythme : seuls les
bonus 4 et 5 supposent d'avoir déclenché au moins un incident (bonus 3).
Les aides et les réponses sont dans les blocs repliés.

Contexte : vous êtes consultant SRE engagé pour auditer **CapShop**, une
boutique e-commerce tech premium qui rencontre des problèmes de fiabilité.

| Bonus | Thème |
|---|---|
| 1 | Découverte de l'architecture |
| 2 | Observabilité : métriques, logs, traces, dashboard |
| 3 | Gestion d'incident et post-mortem |
| 4 | SLOs, error budget et alerte |
| 5 | Réduction du toil |
| 6 | Synthèse : rapport d'audit |

## Prérequis

L'application fil rouge est installée dans votre namespace et les interfaces sont ouvertes :
voir [Installer l'application fil rouge dans EKS](../../AWS_SECURE/README.md), étapes 5 à 8.

Toutes les commandes `kubectl` se lancent sur votre machine
`utils-stagiaireXX`. Les adresses `http://localhost:...` s'ouvrent dans le
navigateur de votre poste, tunnel SSH ouvert. Avec FoxyProxy, remplacez
`localhost` par le nom de la VM (installation, étape 8).

```bash
kubectl get pods
```

Tous les pods doivent être `Running` et prêts (`1/1`).

**Documentation de référence** :
- [Guide Observabilité](../../docs/OBSERVABILITY.md)
- [Guide SLOs et Alerting](../../docs/SLOS_ALERTING.md)
- [Guide Incidents](../../docs/INCIDENTS.md)

---

## Bonus 1 : Découverte de l'architecture

**Objectif** : Comprendre l'architecture et les flux de données

### 1.1 Explorer la boutique CapShop

1. Ouvrez http://localhost:8080
2. Parcourez les catégories de produits
3. Ajoutez des produits au panier
4. Effectuez un achat complet (paiement test)

**Questions** :
- Combien de microservices sont impliqués dans un achat ?
- Quel service gère le panier ?
- Où sont stockées les données du panier ?

<details>
<summary>Réponses</summary>

- **Combien de microservices pour un achat ?** Cinq. La **gateway** reçoit
  `POST /api/orders` et le transmet à **orders**, qui lit le panier dans
  **cart**, appelle **payment**, réserve le stock dans **catalog**, puis
  vide le panier. Users n'intervient pas : la boutique n'a pas de compte client.
- **Quel service gère le panier ?** `cart-service`.
- **Où sont stockées les données du panier ?** Dans **Redis**, pas dans
  PostgreSQL. Un panier est une donnée temporaire : Redis est rapide, mais
  les paniers sont perdus s'il redémarre.

</details>

### 1.2 Identifier les microservices

Listez les 6 microservices et leur rôle, à partir de votre parcours d'achat et de :

```bash
kubectl get deployments,services
```


| Service | Port | Rôle |
|---------|------|------|
| api-gateway | 8080 | ? |
| catalog-service | 8081 | ? |
| cart-service | 8082 | ? |
| orders-service | 8083 | ? |
| payment-service | 8084 | ? |
| users-service | 8085 | ? |

<details>
<summary>Réponses</summary>

| Service | Port | Rôle |
|---------|------|------|
| api-gateway | 8080 | Point d'entrée unique : sert la boutique, route `/api/*` vers les services |
| catalog-service | 8081 | Produits, prix, stock, réservation et réassort automatique |
| cart-service | 8082 | Panier, stocké dans Redis |
| orders-service | 8083 | Orchestration de la commande : panier, paiement, stock |
| payment-service | 8084 | Paiement via un prestataire externe simulé, protégé par un circuit breaker |
| users-service | 8085 | Comptes et authentification JWT |

Pour retrouver une information : `kubectl describe deployment <nom>` (image,
variables d'environnement, probes), `kubectl logs deploy/<nom>`.

</details>

**Livrable** : Tableau des microservices complété (1.2)

---

## Bonus 2 : Observabilité - Les 3 piliers

**Objectif** : Maîtriser Prometheus, Loki et Tempo

### 2.1 Métriques avec Prometheus

1. Ouvrez Prometheus : http://localhost:9090
2. Explorez les métriques disponibles

**Requêtes à exécuter** :

```promql
# Requêtes par seconde par service (vues depuis l'API Gateway)
sum by (service) (rate(gateway_requests_total[5m]))

# Latence P99 des paiements (sans les health checks, bien plus nombreux)
histogram_quantile(0.99, sum by (le) (rate(payment_request_duration_seconds_bucket{endpoint="/api/payments"}[5m])))

# Taux d'erreur global
sum(rate(gateway_requests_total{status=~"5.."}[5m])) / sum(rate(gateway_requests_total[5m]))
```

> Hors incident, le taux d'erreur reste faible, de l'ordre de 0,1 à 0,2 % :
> le prestataire de paiement simulé échoue dans 2 % des paiements, et la
> commande échoue alors en 502.
> Déclenchez un incident depuis l'Operations Console (bonus 3) pour le voir
> monter.
>
> La gateway ne compte que le trafic des clients. Les appels entre services
> (orders vers payment, cart vers catalog...) n'y figurent pas. Le trafic total
> d'un service se lit dans ses propres métriques, sans les health checks.
> Pour comparer, découpez par route :
> `sum by (method) (rate(gateway_requests_total{service="payment"}[5m]))` et
> `sum by (method, endpoint) (rate(payment_requests_total{endpoint!~"/health|/ready|/metrics"}[5m]))`.

**Questions** :
- Quel service reçoit le plus de requêtes ?
- Pour payment, comparez le trafic vu par la gateway et celui mesuré par le service lui-même. D'où vient l'écart ?
- Quelle est la latence moyenne du catalog ? (`rate(catalog_request_duration_seconds_sum[5m]) / rate(catalog_request_duration_seconds_count[5m])`)

<details>
<summary>Ça bloque ?</summary>

- **La requête ne renvoie rien** : vérifiez la période en haut à droite
  (dernière heure) et que le générateur de trafic tourne
  (`kubectl get pods -l app=traffic-generator`).
- **`gateway_requests_total` est vide** : laissez tourner l'application 5 minutes,
  `rate(...[5m])` a besoin d'historique.
- **Un service manque** dans la première requête : il n'a pas reçu de trafic
  client récemment, ou il est en panne (`kubectl get pods`).

</details>

<details>
<summary>Réponses</summary>

- **Service le plus sollicité** : **catalog**. Tout le monde consulte les
  produits, peu de gens achètent.
- **Écart gateway / service pour payment** : les deux débits sont proches,
  mais ne mesurent pas la même chose. Découpé par route, la gateway ne voit
  que des `GET /api/circuit-breaker` (des clients qui consultent l'état du
  circuit breaker) et **aucun paiement**. Le service, lui, reçoit en plus
  les `POST /api/payments`, envoyés par **orders** à l'intérieur du
  cluster, sans passer par la gateway. Un total peut sembler cohérent tout
  en cachant un trafic complètement différent : une observabilité limitée
  au point d'entrée ne voit pas le trafic entre services.
- **Latence moyenne du catalog** : quelques millisecondes à quelques dizaines
  hors incident. Une moyenne cache les requêtes lentes, d'où l'usage du P99
  pour les SLOs.

</details>

### 2.2 Logs avec Loki

1. Ouvrez Grafana : http://localhost:3000
2. Dans le menu de gauche, cliquez sur **Explore**
3. En haut à gauche, choisissez la source de données **Loki**
4. Dans la zone de requête, passez de **Builder** à **Code** (bouton à droite
   de la zone), puis collez une requête
5. Cliquez sur **Run query** en haut à droite. La période affichée se règle à
   côté (par défaut, la dernière heure)

Les lignes commençant par `#` sont des commentaires : collez une requête à la
fois.

**Requêtes à exécuter** :

```logql
# Tous les logs du payment service
{job="payment-service"}

# Erreurs uniquement (codes 4xx/5xx)
{job="payment-service"} |~ " [45][0-9]{2} "

# Requêtes lentes ou en timeout sur l'api-gateway
{job="api-gateway"} |~ "(?i)(slow|timeout|error)"
```

**Questions** :
- Combien de logs d'erreur dans les 15 dernières minutes ?
- Quel type d'erreur est le plus fréquent ?

<details>
<summary>Ça bloque ?</summary>

- **« No data »** : élargissez la période, puis vérifiez la source **Loki**
  en haut à gauche.
- **`{job="payment-service"}` ne renvoie rien** : le label `job` vaut le nom
  du container. Dans le **Label browser**, regardez les valeurs disponibles.
- **Trop de lignes** : ajoutez `!= "/health"` pour écarter les health checks.

</details>

<details>
<summary>Réponses</summary>

- **Nombre de logs d'erreur** : dépend du moment, faible hors incident.
  Pour le compter, passez en requête de métrique :
  `sum(count_over_time({job="payment-service"} |~ " [45][0-9]{2} " [15m]))`.
- **Erreur la plus fréquente** : hors incident, l'échec aléatoire du
  prestataire de paiement (`External payment provider temporarily
  unavailable`, 2 % des paiements). Orders renvoie alors un 502, que la
  boutique affiche comme « Paiement refusé ». Côté gateway, les 4xx
  viennent du générateur de trafic : 404 quand il retire du panier un
  article absent, 400 quand il commande avec un panier vide.

</details>

### 2.3 Traces avec Tempo

1. Dans Grafana, allez dans Explore → Tempo, onglet **TraceQL**
2. Filtrez les checkouts parmi les traces de `api-gateway` :

```traceql
{ resource.service.name = "api-gateway" && name = "POST /api/orders" }
```

Sans filtre sur le nom de la requête, les checkouts sont noyés parmi les
consultations de produits et les health checks `/health`.

**Exercice** :
- Trouvez une trace d'un checkout complet
- Identifiez tous les services traversés
- Mesurez le temps passé dans chaque service

<details>
<summary>Ça bloque ?</summary>

- **Pas de trace** : passez une commande dans la boutique, puis attendez
  une minute. Élargissez la période à la dernière heure.
- **Ouvrir une trace** : cliquez sur son identifiant dans la liste des
  résultats. La vue en cascade (« waterfall ») montre chaque span avec sa
  durée.

</details>

<details>
<summary>Réponses</summary>

Une trace de checkout traverse **api-gateway → orders-service**, puis
orders appelle successivement **cart-service** (lecture du panier),
**payment-service** (paiement), **catalog-service** (réservation du stock,
une fois par article), puis de nouveau **cart-service** (vidage du panier).

Hors incident, le paiement occupe l'essentiel du temps : 100 à 500 ms
d'appel au prestataire simulé. Les autres appels prennent quelques
millisecondes.

</details>

**Livrable** : Screenshot d'une trace annotée

### 2.4 Améliorer le dashboard

Un dashboard basique "SRE Overview" est déjà provisionné dans Grafana, mais il est insuffisant pour un suivi opérationnel. Complétez-le (ou dupliquez-le sous le nom "Reskilling Overview") pour qu'il contienne :

1. **Panel Latence** (Time series)
   - P50, P90, P99 par service
   
2. **Panel Taux d'erreur** (Gauge)
   - Couleur verte < 1%, orange < 5%, rouge >= 5%

3. **Panel Trafic** (Stat)
   - Requêtes/seconde total

4. **Panel Logs récents** (Logs panel)
   - Derniers logs d'erreur

La marche à suivre (copier le dashboard, ajouter un panel) est dans
le [Guide Observabilité](../../docs/OBSERVABILITY.md#4-grafana---dashboards).

<details>
<summary>Réponses</summary>

Requêtes possibles pour chaque panel, à adapter :

```promql
histogram_quantile(0.99, sum by (le, service) (rate(gateway_request_duration_seconds_bucket[5m])))
100 * sum(rate(gateway_requests_total{status=~"5.."}[5m])) / sum(rate(gateway_requests_total[5m]))
sum(rate(gateway_requests_total[5m]))
```

```logql
{job=~"api-gateway|.+-service"} |~ "(?i)error| 5[0-9]{2} "
```

Pour P50 et P90, remplacez `0.99`. Le taux d'erreur doit rester vert hors
incident (environ 0,2 %) et passer à l'orange ou au rouge pendant un
incident.

</details>


---

## Bonus 3 : Gestion d'incident

**Objectif** : Gérer un incident de bout en bout

### 3.1 Déclencher un incident

1. Ouvrez l'Operations Console : http://localhost:8090
2. Notez l'heure de début
3. Cliquez sur la carte **Latence élevée du service de paiement**

### 3.2 Détecter et trier

**Checklist** :
- [ ] Vérifier les alertes dans Alertmanager (http://localhost:9093)
- [ ] Identifier le service impacté
- [ ] Évaluer la sévérité (P1-P4)
- [ ] Quantifier l'impact utilisateur

<details>
<summary>Réponses</summary>

- **Alertes attendues** au bout de quelques minutes :
  `PaymentServiceHighLatency` (P95 des paiements > 1 s),
  `HighLatencyP99Orders` (commandes > 1,5 s), et votre alerte SLO
  si vous avez fait le bonus 4.
- **Service impacté** : `payment-service`. Orders et la gateway sont lents
  parce qu'ils l'attendent.
- **Sévérité** : P1 ou P2. Le paiement fonctionne encore, mais chaque achat
  prend plus de 3 secondes : c'est le chiffre d'affaires qui est touché.
  P1 si vous considérez que les clients abandonnent.
- **Impact utilisateur** : tous les clients qui paient. La navigation et le
  panier ne sont pas touchés.

</details>

### 3.3 Investiguer

Utilisez les 3 piliers :

**Métriques** (Prometheus) :
```promql
# Latence des paiements
histogram_quantile(0.99, sum by (le) (rate(payment_request_duration_seconds_bucket{endpoint="/api/payments"}[1m])))
```

**Logs** (Loki) :
```logql
{job="payment-service"} |~ "(?i)(slow|timeout|error)"
```

**Traces** (Tempo) :
- Trouvez une trace lente :

```traceql
{ resource.service.name = "payment-service" && duration > 1s }
```

- Identifiez le span problématique

<details>
<summary>Ça bloque ?</summary>

- **Aucune trace lente** : attendez une ou deux minutes après le
  déclenchement, puis élargissez la période.
- **Logs** : cherchez aussi `slow`, le service journalise
  `External payment provider slow response` au-delà d'une seconde.

</details>

<details>
<summary>Réponses</summary>

- **Métriques** : le P99 du paiement passe d'environ 0,5 s à plus de 3 s.
- **Logs** : `External payment provider slow response: 3.xx s`.
- **Traces** : dans le span `process_payment` de payment-service, l'attente
  du prestataire externe représente presque toute la durée.
  Les spans de catalog et cart restent rapides.

Le circuit breaker, lui, reste **fermé** (`circuit_breaker_state` = 0) : il
ne s'ouvre que sur des **erreurs**, pas sur de la lenteur. C'est une
protection manquante à noter dans le post-mortem : un timeout plus court
sur l'appel au prestataire transformerait la lenteur en erreurs, et le
circuit breaker pourrait alors protéger le système.

</details>

### 3.4 Résoudre

1. Dans l'Operations Console, ouvrez l'incident et cliquez **Mark Resolved**
2. Vérifiez le retour à la normale dans Grafana
3. Notez l'heure de résolution

<details>
<summary>Ça bloque ?</summary>

- **La carte ne déclenche rien** : vérifiez que l'onglet **Incidents**
  affiche l'incident en cours, puis consultez les logs
  `kubectl logs deploy/lab-controller --tail 50`.
- **Le retour à la normale tarde** : les requêtes sur `[5m]` mettent jusqu'à
  5 minutes à redescendre. Ce n'est pas un échec de la résolution.

</details>

### 3.5 Documenter le post-mortem

Dans l'onglet **Incidents**, ouvrez l'incident résolu et cliquez sur
*Generate Post-Mortem*. Le post-mortem apparaît dans l'onglet
**Post-Mortems**. La console ne produit qu'un **squelette** : elle calcule ce
qu'elle sait (impact, durée, services, timeline) et laisse vide tout ce qui
relève de l'analyse. C'est vous qui rédigez le post-mortem.

Le compteur `n/12 sections` en haut de chaque fiche indique ce qu'il reste à
compléter. Cliquez sur **Éditer**.

| Section | Origine | À votre charge |
|---------|---------|----------------|
| Impact, durée, services | calculés depuis l'incident | non |
| Timeline | calculée depuis l'incident | non |
| Participants | issus des témoignages | non |
| Cause racine | vide (pistes des témoins fournies) | **oui** |
| Élément déclencheur | vide | **oui** |
| Réaction du système | vide | **oui** |
| Protections manquantes | vide | **oui** |
| Impact utilisateur | vide | **oui** |
| Détection | vide | **oui** |
| Résolution | vide | **oui** |
| Ce qui a bien fonctionné | vide | **oui** |
| Ce qui a mal fonctionné | vide | **oui** |
| Où nous avons eu de la chance | vide | **oui** |
| Enseignements | vide | **oui** |
| Actions correctives | vide | **oui** (3 minimum) |

Les actions se saisissent une par ligne, au format
`tâche | type | priorité | responsable | échéance`, où *type* vaut
`prevent` (empêcher la récurrence), `mitigate` (limiter l'impact) ou
`detect` (raccourcir la détection).

> **Cause racine.** Elle décrit un mécanisme, pas un symptôme. « Le service
> était lent » est un symptôme ; « le pool de connexions était dimensionné à 10
> alors que le pic demande 30 » est une cause racine.

> **Où nous avons eu de la chance.** Section souvent oubliée, et pourtant la
> plus révélatrice : qu'est-ce qui aurait pu aggraver l'incident et ne s'est pas
> produit ? Un incident survenu en heures ouvrées, un cache encore chaud, une
> dépendance qui n'a pas cédé. Chaque réponse désigne une fragilité non traitée.

> **Post-mortem sans blame.** Décrivez les décisions avec l'information
> disponible au moment des faits, pas avec le recul. On ne cherche pas un
> responsable, mais un système qui a permis l'erreur.

Passez le statut à *Final* quand votre analyse est complète.

<details>
<summary>Réponses</summary>

Points attendus pour l'incident de latence du paiement :

- **Cause racine** : la latence du prestataire de paiement externe a
  augmenté d'environ 3 secondes, et rien dans notre système ne la limitait.
  Le symptôme est « le paiement est lent », la cause est « aucun timeout
  court ni repli sur l'appel externe ».
- **Témoignages à vérifier.** Les témoins donnent des pistes, pas des faits.
  Bob affirme que le circuit breaker est passé en OPEN : les métriques
  montrent qu'il est resté fermé. Le post-mortem s'appuie sur les mesures.
- **Protections manquantes** : timeout court sur l'appel externe, circuit
  breaker déclenché aussi par la latence, alerte de latence plus tôt dans
  la chaîne.
- **Où nous avons eu de la chance** : pas d'erreur, seulement de la
  lenteur. Les commandes ont fini par passer. Avec un prestataire
  totalement bloqué, le timeout d'orders (10 s) aurait accumulé les
  requêtes en attente.
- **MTTR** = heure de résolution − heure de début. La console le calcule
  dans l'onglet Incidents. Comparez-le avec le délai de détection (début →
  première alerte).
- **Actions correctives**, par exemple :
  `Timeout de 1 s sur l'appel au prestataire | prevent | P1 | équipe paiement | J+7`,
  `Alerte sur la latence P99 du prestataire | detect | P2 | SRE | J+14`,
  `Message d'attente côté boutique au-delà de 2 s | mitigate | P3 | front | J+30`.

</details>

**Livrable** : Post-mortem complété + MTTR calculé

---

## Bonus 4 : Définition des SLOs

**Objectif** : Définir des SLOs réalistes basés sur les données

### 4.1 Analyser les métriques historiques

Utilisez Prometheus pour analyser l'historique disponible. Élargissez la
fenêtre à `[24h:5m]` si l'application tourne depuis plus d'une journée.

```promql
# Disponibilité par service
avg_over_time(
  (sum by (service) (rate(gateway_requests_total{status!~"5.."}[5m])) 
   / sum by (service) (rate(gateway_requests_total[5m])))[1h:5m]
)

# Latence P99 moyenne (gateway, tous services confondus)
avg_over_time(
  histogram_quantile(0.99, sum by (le) (rate(gateway_request_duration_seconds_bucket[5m])))[1h:5m]
)
```

> Pour que ces mesures aient du sens, faites tourner au moins un incident
> (bonus 3) avant de figer vos SLOs : sans erreur observée, la disponibilité
> mesurée vaut 100 % et l'error budget du bonus 4.3 est ininterprétable.

<details>
<summary>Ça bloque ?</summary>

- **Résultat vide** : la fenêtre `[1h:5m]` demande une heure de données.
  Réduisez à `[30m:5m]` si l'application vient d'être installée.
- **Disponibilité à 1 (100 %)** : aucune erreur 5xx sur la période,
  déclenchez d'abord un incident (bonus 3).
- **Lire une valeur** : onglet **Table** de Prometheus. `0.998` signifie
  99,8 %.

</details>

### 4.2 Définir les SLOs

Pour chaque service, définissez :

| Service | SLI | SLO | Justification business |
|---------|-----|-----|------------------------|
| catalog | Disponibilité | ?% | Navigation produits |
| catalog | Latence P99 | ?ms | UX fluide |
| cart | Disponibilité | ?% | Conversion critique |
| payment | Disponibilité | ?% | Revenus |
| payment | Latence P99 | ?ms | Checkout rapide |

**Règles** :
- Basez-vous sur les données réelles
- Ajoutez une marge de sécurité (5-10%)
- Justifiez chaque choix

<details>
<summary>Réponses</summary>

Exemple de tableau raisonnable. Vos chiffres dépendent de vos mesures :
l'important est la justification.

| Service | SLI | SLO | Justification |
|---------|-----|-----|---------------|
| catalog | Disponibilité | 99,5 % | Navigation : une erreur ponctuelle se rattrape par un rechargement |
| catalog | Latence P99 | 300 ms | Mesuré autour de quelques dizaines de ms, large marge |
| cart | Disponibilité | 99,5 % | Un panier qui échoue fait perdre la vente |
| payment | Disponibilité | 97 % | Le prestataire externe échoue déjà dans 2 % des paiements : même 98 % ne laisse aucune marge sans retry |
| payment | Latence P99 | 1 s | Mesuré entre 100 et 500 ms, l'appel externe domine |

La requête de 4.1 mesure ce que voit la gateway, qui ne voit pas les
paiements (bonus 2.1) : pour payment, elle donne près de 100 %. Mesurez
plutôt sur `payment_requests_total{endpoint="/api/payments"}`.

Erreurs fréquentes :
- un SLO à 100 % : aucun budget d'erreur, chaque incident est un échec ;
- un SLO plus strict que ce que le système fait déjà : alerte permanente ;
- oublier que payment dépend d'un tiers dont on ne maîtrise pas la fiabilité.

</details>

### 4.3 Calculer l'Error Budget

Pour votre SLO principal (par exemple la disponibilité de catalog, 99,5 %) :

```
Error Budget = (100% - SLO%) × Période
```

**Calculez** :
- Budget mensuel (en minutes)
- Budget consommé actuellement
- Budget restant

<details>
<summary>Réponses</summary>

Pour un SLO de 99,5 % sur 30 jours :

- **Budget mensuel** : 0,5 % × 30 j × 24 h × 60 min = **216 minutes**
  d'indisponibilité tolérée.
- **Budget consommé** : la part d'erreurs observée, ramenée à la période.
  Par exemple, un incident de 20 minutes avec 30 % d'erreurs consomme
  20 × 0,3 = **6 minutes** de budget.
- **Budget restant** : 216 − 6 = **210 minutes**, soit 97 % du budget.

En PromQL, le budget consommé sur la période observée :

```promql
1 - (sum(increase(gateway_requests_total{service="catalog",status!~"5.."}[1h]))
     / sum(increase(gateway_requests_total{service="catalog"}[1h])))
```

à comparer au 0,5 % autorisé.

</details>

### 4.4 Configurer une alerte SLO

Créez une règle d'alerte pour votre SLO :

Sur `utils-stagiaireXX`, créez le fichier `my_slo_alerts.yml`, en adaptant le
seuil au SLO que vous avez défini :

```yaml
groups:
  - name: my_slo_alerts
    rules:
      - alert: PaymentSLOBreach
        expr: histogram_quantile(0.99, sum by (le) (rate(payment_request_duration_seconds_bucket{endpoint="/api/payments"}[5m]))) > 1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Latence P99 du paiement au-delà du SLO"
          description: "P99 à {{ $value | humanizeDuration }}, seuil 1 s."
```

Validez la règle avec l'outil de Prometheus, dans son pod :

```bash
kubectl exec -i deploy/prometheus -- sh -c 'cat > /tmp/regle.yml && promtool check rules /tmp/regle.yml' < my_slo_alerts.yml
```

Les règles de Prometheus sont dans la ConfigMap `prometheus-rules`. Ajoutez-y
votre fichier :

```bash
kubectl patch configmap prometheus-rules --type merge \
  --patch "$(printf 'data:\n  my_slo_alerts.yml: |\n'; sed 's/^/    /' my_slo_alerts.yml)"
```

Le fichier apparaît dans le pod au bout d'une minute environ :

```bash
kubectl exec deploy/prometheus -- ls /etc/prometheus/rules/
```

Quand `my_slo_alerts.yml` est présent, rechargez Prometheus :

```bash
curl --request POST http://localhost:9090/-/reload
```

La règle apparaît dans http://localhost:9090/alerts. Elle survit à un
`helm upgrade`, qui ne touche pas aux clés qu'il n'a pas créées, mais pas à
une réinstallation (`helm uninstall` puis `helm install`) : il faut alors
l'ajouter de nouveau.

<details>
<summary>Ça bloque ?</summary>

- **`promtool` signale une erreur** : le plus souvent l'indentation. YAML
  exige des espaces, jamais de tabulations.
- **Le fichier n'apparaît pas dans le pod** : la mise à jour de la ConfigMap
  prend jusqu'à une minute. Vérifiez qu'elle contient votre clé :
  `kubectl get configmap prometheus-rules -o yaml | grep my_slo`.
- **`curl .../-/reload` ne répond pas** : le port-forward de Prometheus est
  tombé, relancez-le (voir l'étape 8 de l'installation).
- **La règle est `inactive`** : c'est normal, elle passe `pending` puis
  `firing` seulement quand la condition est vraie pendant 5 minutes.
  Déclenchez l'incident du bonus 3 pour la voir s'activer.

</details>

**Livrable** : Tableau des SLOs + fichier de règles

---

## Bonus 5 : Réduction du Toil

**Objectif** : Identifier et automatiser le toil

### 5.1 Identifier le toil

Dans l'Operations Console, onglet "Automation" :

1. Listez les tâches répétitives identifiées
2. Pour chaque tâche, notez :
   - Fréquence (par jour/semaine)
   - Temps manuel estimé
   - Est-ce automatisable ? (oui/partiellement/non)

<details>
<summary>Réponses</summary>

L'onglet Automation propose cinq tâches, toutes déclenchées par incident :

| Tâche | Temps manuel |
|---|---|
| Restart manuel des pods en CrashLoopBackOff | 15 min |
| Vérification manuelle des logs après incident | 30 min |
| Reset manuel du circuit breaker | 5 min |
| Collecte des métriques pour le post-mortem | 20 min |
| Notification des stakeholders | 10 min |

Toutes sont automatisables, au moins partiellement. L'analyse des logs
reste en partie humaine : on peut automatiser la collecte, pas la
compréhension.

</details>

### 5.2 Prioriser

Calculez le score de priorité :

```
Score = Fréquence × Temps × Automatisabilité
```

Les tâches de l'onglet Automation sont déclenchées par incident. Convertissez
leur fréquence en occurrences par semaine à partir du nombre d'incidents
observés, puis remplissez :

| Tâche | Fréquence | Temps | Auto (0-1) | Score |
|-------|-----------|-------|------------|-------|
| Notification des stakeholders | ? /semaine | 10 min | ? | ? |
| Vérification des logs après incident | ? /semaine | ? min | ? | ? |
| ... | ... | ... | ... | ... |

<details>
<summary>Réponses</summary>

Exemple avec 3 incidents par semaine :

| Tâche | Fréquence | Temps | Auto | Score |
|---|---|---|---|---|
| Vérification des logs | 3 /sem | 30 min | 0,5 | 45 |
| Collecte des métriques | 3 /sem | 20 min | 0,9 | 54 |
| Restart des pods | 3 /sem | 15 min | 0,8 | 36 |
| Notification | 3 /sem | 10 min | 0,9 | 27 |
| Reset du circuit breaker | 3 /sem | 5 min | 1 | 15 |

La **collecte des métriques pour le post-mortem** sort en tête : longue,
répétitive et entièrement automatisable. Les logs prennent plus de temps,
mais leur analyse ne s'automatise qu'en partie.

</details>

### 5.3 Automatiser

Choisissez la tâche avec le score le plus élevé et écrivez un script :

**Exemple : Health check automatique**

```bash
#!/bin/bash
# health_monitor.sh

for deploy in api-gateway catalog-service cart-service orders-service payment-service users-service; do
    desired=$(kubectl get deployment "$deploy" --output jsonpath='{.spec.replicas}')
    ready=$(kubectl get deployment "$deploy" --output jsonpath='{.status.readyReplicas}')

    if [ "${ready:-0}" -lt "$desired" ]; then
        echo "$(date) - $deploy : ${ready:-0}/$desired prêt, redémarrage..."
        kubectl rollout restart deployment/"$deploy"
    fi
done
```

Testez-le en provoquant une panne de la base de données :

```bash
kubectl scale statefulset postgres --replicas=0
kubectl get pods --watch      # attendez que des services passent à 0/1, puis Ctrl+C
bash health_monitor.sh
kubectl scale statefulset postgres --replicas=1
```

**Questions** :
- Quels services le script relance-t-il, et pourquoi ceux-là ?
- Les relancer suffit-il à rétablir le service ?
- Kubernetes relance déjà un container dont la liveness probe échoue :
  qu'apporte ce script en plus, et qu'automatiseriez-vous plutôt ?

<details>
<summary>Ça bloque ?</summary>

- **Le script ne relance rien** : il est passé trop tôt. La readiness met
  une trentaine de secondes à échouer après l'arrêt de postgres ;
  relancez-le quand des pods sont à `0/1`.
- **`readyReplicas` vide** : aucun pod n'est prêt, le script le traite comme
  0 grâce à `${ready:-0}`.
- **Les pods ne redeviennent pas prêts** après `--replicas=1` : postgres met
  une trentaine de secondes à démarrer. Suivez avec
  `kubectl get pods --watch`.
- **L'application fil rouge reste dégradée** : relancez le script une fois postgres revenu, ou
  `kubectl rollout restart deployment/<nom>`.

</details>

<details>
<summary>Réponses</summary>

- **Services relancés** : catalog, orders et users. Leur readiness probe
  vérifie la base : postgres arrêté, ils ne sont plus prêts.
- **Est-ce suffisant ?** Non. La panne vient de la base de données, pas de
  ces services. Relancés, ils restent non prêts tant que postgres est
  arrêté. Pire, chaque redémarrage coupe les requêtes en cours : le script
  aggrave l'incident.
- **Ce qu'il apporte en plus de Kubernetes** : rien d'utile. Kubernetes
  relance déjà un container bloqué (`liveness`) et retire du trafic un pod
  non prêt (`readiness`). Mieux vaut automatiser la **détection et le
  diagnostic** : repérer la dépendance en panne (`pg_up == 0`, `up == 0`),
  rassembler les events et les logs des pods concernés, prévenir l'équipe.
  La tâche de collecte des métriques (5.2) en est un bon exemple.

</details>

### 5.4 Mesurer l'impact

Après automatisation, calculez :
- Temps gagné par semaine
- Réduction du toil (%)

<details>
<summary>Réponses</summary>

Pour la collecte des métriques automatisée, avec 3 incidents par semaine :

- **Temps gagné** : 3 × 20 min × 0,9 = **54 minutes par semaine**.
- **Réduction du toil** : 54 min sur un toil total de
  3 × (15 + 30 + 5 + 20 + 10) = 240 min, soit **environ 22 %**.

Retirez de ce gain le temps d'écriture et de maintenance du script :
c'est le retour sur investissement.

</details>

**Livrable** : Script d'automatisation + estimation temps gagné

---

## Bonus 6 : Synthèse et présentation

**Objectif** : Synthétiser les apprentissages

### 6.1 Préparer un rapport d'audit

Créez un document contenant :

1. **État des lieux**
   - Architecture actuelle
   - Points forts
   - Points faibles

2. **SLOs proposés** (si vous avez fait le bonus 4)
   - Tableau des SLOs par service
   - Justifications business

3. **Observabilité**
   - Dashboards créés
   - Alertes configurées

4. **Gestion d'incidents**
   - Workflow documenté
   - Template de post-mortem

5. **Automatisation**
   - Toil identifié
   - Scripts développés
   - ROI estimé

<details>
<summary>Ça bloque ?</summary>

Reprenez vos livrables : tableau des services (1.2), dashboard (2.4),
post-mortem (3), SLOs et règle d'alerte (4, si faits), script et calcul de
gain (5). Le
rapport les assemble, il ne demande pas de nouvelle manipulation.

</details>

### 6.2 Recommandations

Proposez 5 améliorations prioritaires :

| # | Amélioration | Impact | Effort | Priorité |
|---|--------------|--------|--------|----------|
| 1 | ? | Haut/Moyen/Bas | H/M/B | P1-P4 |
| 2 | ? | ? | ? | ? |
| ... | ... | ... | ... | ... |

<details>
<summary>Réponses</summary>

Exemples de recommandations, à adapter à vos constats :

| # | Amélioration | Impact | Effort | Priorité |
|---|---|---|---|---|
| 1 | Timeout court et circuit breaker déclenché par la latence sur l'appel au prestataire de paiement | Haut | B | P1 |
| 2 | Alertes basées sur le burn rate des SLOs plutôt que sur des seuils fixes | Haut | M | P1 |
| 3 | Instrumenter les appels entre services (vus de l'appelant) en plus de la gateway | Moyen | M | P2 |
| 4 | Persistance et sauvegarde de PostgreSQL, unique point de défaillance de trois services | Haut | M | P2 |
| 5 | Collecte automatique des métriques pour les post-mortems | Moyen | B | P3 |

</details>

**Livrable** : Rapport d'audit complet

---

## Livrables des bonus

| Bonus | Livrable |
|-------|----------|
| 1. Architecture | Tableau des microservices complété |
| 2. Observabilité | Dashboard "Reskilling Overview" complété et fonctionnel |
| 3. Incident | Post-mortem complet avec MTTR calculé |
| 4. SLOs | Tableau de SLOs justifiés + fichier de règles d'alerte |
| 5. Toil | Script d'automatisation fonctionnel |
| 6. Synthèse | Rapport d'audit avec recommandations priorisées |

---

## Ressources

- [Google SRE Book](https://sre.google/sre-book/table-of-contents/)
- [SRE Workbook](https://sre.google/workbook/table-of-contents/)
- [Prometheus Docs](https://prometheus.io/docs/)
- [Grafana Docs](https://grafana.com/docs/)
- [Loki Docs](https://grafana.com/docs/loki/)
- [Tempo Docs](https://grafana.com/docs/tempo/)
