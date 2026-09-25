# Exercices pratiques - Reskilling SRE Lab

## Contexte du lab

Vous êtes consultant SRE engagé pour auditer **CapShop**, une boutique e-commerce tech premium. Le site rencontre des problèmes de fiabilité et vous devez :

1. Mettre en place une observabilité efficace
2. Définir des SLOs pertinents
3. Gérer des incidents en conditions réelles
4. Proposer des automatisations

## Prérequis

Lab demarre et operationnel : voir [QUICKSTART.md](../QUICKSTART.md).

```bash
make start
make test
```

**Documentation de référence** :
- [Guide Observabilité](../docs/OBSERVABILITY.md)
- [Guide SLOs et Alerting](../docs/SLOS_ALERTING.md)
- [Guide Incidents](../docs/INCIDENTS.md)

---

## Exercice 1 : Découverte de l'architecture

**Durée** : 30 min  
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

### 1.2 Identifier les microservices

Listez les 6 microservices et leur rôle, à partir de `docker-compose.yml` et de votre parcours d'achat :

| Service | Port | Rôle |
|---------|------|------|
| api-gateway | 8080 | ? |
| catalog-service | 8081 | ? |
| cart-service | 8082 | ? |
| orders-service | 8083 | ? |
| payment-service | 8084 | ? |
| users-service | 8085 | ? |

**Livrable** : Tableau des microservices complété (1.2)

---

## Exercice 2 : Observabilité - Les 3 piliers

**Durée** : 45 min  
**Objectif** : Maîtriser Prometheus, Loki et Tempo

### 2.1 Métriques avec Prometheus

1. Ouvrez Prometheus : http://localhost:9090
2. Explorez les métriques disponibles

**Requêtes à exécuter** :

```promql
# Requêtes par seconde par service (vues depuis l'API Gateway)
sum by (service) (rate(gateway_requests_total[5m]))

# Latence P99 du service payment
histogram_quantile(0.99, sum by (le) (rate(payment_request_duration_seconds_bucket[5m])))

# Taux d'erreur global
sum(rate(gateway_requests_total{status=~"5.."}[5m])) / sum(rate(gateway_requests_total[5m]))
```

> Hors incident, cette requete ne renvoie aucune serie: c'est normal, le lab
> ne produit pas d'erreur en regime nominal. Declenchez un incident depuis
> l'Operations Console (exercice 4) pour la voir remonter des valeurs.
>
> Rappel: la gateway ne compte que le trafic qui la traverse. Le trafic
> interne entre services n'y figure pas, ce qui fait apparaitre le catalogue
> comme le service le plus sollicite.

**Questions** :
- Quel service reçoit le plus de requêtes ?
- Quelle est la latence moyenne du catalog ? (`rate(catalog_request_duration_seconds_sum[5m]) / rate(catalog_request_duration_seconds_count[5m])`)

### 2.2 Logs avec Loki

1. Ouvrez Grafana : http://localhost:3000
2. Allez dans Explore → Loki

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

### 2.3 Traces avec Tempo

1. Dans Grafana, allez dans Explore → Tempo
2. Cherchez des traces du service `api-gateway`

**Exercice** :
- Trouvez une trace d'un checkout complet
- Identifiez tous les services traversés
- Mesurez le temps passé dans chaque service

**Livrable** : Screenshot d'une trace annotée

### 2.4 Améliorer le dashboard

Un dashboard basique "SRE Overview" est déjà provisionné dans Grafana, mais il est insuffisant pour un suivi opérationnel. Complétez-le (ou dupliquez-le sous le nom "Reskilling Overview") pour qu'il contienne :

1. **Panel Latence** (Time series)
   - P50, P90, P99 par service
   
2. **Panel Taux d'erreur** (Gauge)
   - Couleur verte < 1%, orange < 5%, rouge >= 5%

3. **Panel Traffic** (Stat)
   - Requêtes/seconde total

4. **Panel Logs récents** (Logs panel)
   - Derniers logs d'erreur

**Livrable** : Dashboard exporté (JSON)

---

## Exercice 3 : Définition des SLOs

**Durée** : 45 min  
**Objectif** : Définir des SLOs réalistes basés sur les données

### 3.1 Analyser les métriques historiques

Utilisez Prometheus pour analyser l'historique disponible. Elargissez la
fenetre a `[24h:5m]` si le lab tourne depuis plus d'une journee.

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
> (exercice 4) avant de figer vos SLOs: sans erreur observee, la disponibilite
> mesuree vaut 100% et l'error budget de l'exercice 3.3 est ininterpretable.

### 3.2 Définir les SLOs

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

### 3.3 Calculer l'Error Budget

Pour votre SLO principal (ex: payment 99.5%) :

```
Error Budget = (100% - SLO%) × Période
```

**Calculez** :
- Budget mensuel (en minutes)
- Budget consommé actuellement
- Budget restant

### 3.4 Configurer une alerte SLO

Créez une règle d'alerte pour votre SLO :

Creez un fichier dans `observability/prometheus/rules/`, en adaptant le seuil
au SLO que vous avez defini :

```yaml
groups:
  - name: my_slo_alerts
    rules:
      - alert: PaymentSLOBreach
        expr: histogram_quantile(0.99, sum by (le) (rate(payment_request_duration_seconds_bucket[5m]))) > 0.3
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Latence P99 du paiement au-dela du SLO"
          description: "P99 a {{ $value | humanizeDuration }}, seuil 300ms."
```

Validez avant de recharger Prometheus :

```bash
docker compose exec prometheus promtool check rules /etc/prometheus/rules/votre-fichier.yml
docker compose restart prometheus
```

**Livrable** : Tableau des SLOs + fichier de règles

---

## Exercice 4 : Gestion d'incident

**Durée** : 60 min  
**Objectif** : Gérer un incident de bout en bout

### 4.1 Déclencher un incident

1. Ouvrez l'Operations Console : http://localhost:8090
2. Notez l'heure de début
3. Cliquez sur la carte **Latence élevée du service de paiement**

### 4.2 Détecter et trier

**Checklist** :
- [ ] Vérifier les alertes dans Alertmanager
- [ ] Identifier le service impacté
- [ ] Évaluer la sévérité (P1-P4)
- [ ] Quantifier l'impact utilisateur

### 4.3 Investiguer

Utilisez les 3 piliers :

**Métriques** (Prometheus) :
```promql
# Latence du service impacté
histogram_quantile(0.99, sum by (le) (rate(payment_request_duration_seconds_bucket[1m])))
```

**Logs** (Loki) :
```logql
{job="payment-service"} |~ "(?i)(slow|timeout|error)"
```

**Traces** (Tempo) :
- Trouvez une trace lente
- Identifiez le span problématique

### 4.4 Résoudre

1. Dans l'Operations Console, ouvrez l'incident et cliquez **Mark Resolved**
2. Vérifiez le retour à la normale dans Grafana
3. Notez l'heure de résolution

### 4.5 Documenter le post-mortem

Dans l'onglet **Post-Mortems**, cliquez sur *Generate Post-Mortem* depuis
l'incident resolu. La console ne produit qu'un **squelette**: elle calcule ce
qu'elle sait (impact, duree, services, timeline) et laisse vide tout ce qui
releve de l'analyse. C'est vous qui redigez le post-mortem.

Le compteur `n/12 sections` en haut de chaque fiche indique ce qu'il reste a
completer. Cliquez sur **Éditer**.

| Section | Origine | A votre charge |
|---------|---------|----------------|
| Impact, duree, services | calcules depuis l'incident | non |
| Timeline | calculee depuis l'incident | non |
| Participants | issus des temoignages | non |
| Cause racine | vide (pistes des temoins fournies) | **oui** |
| Element declencheur | vide | **oui** |
| Reaction du systeme | vide | **oui** |
| Protections manquantes | vide | **oui** |
| Impact utilisateur | vide | **oui** |
| Detection / Resolution | vide | **oui** |
| Ce qui a bien fonctionne | vide | **oui** |
| Ce qui a mal fonctionne | vide | **oui** |
| Ou nous avons eu de la chance | vide | **oui** |
| Enseignements | vide | **oui** |
| Actions correctives | vide | **oui** (3 minimum) |

Les actions se saisissent une par ligne, au format
`tache | type | priorite | responsable | echeance`, ou *type* vaut
`prevent` (empecher la recurrence), `mitigate` (limiter l'impact) ou
`detect` (raccourcir la detection).

> **Cause racine.** Elle decrit un mecanisme, pas un symptome. « Le service
> etait lent » est un symptome; « le pool de connexions etait dimensionne a 10
> alors que le pic demande 30 » est une cause racine.

> **Ou nous avons eu de la chance.** Section souvent oubliee, et pourtant la
> plus revelatrice: qu'est-ce qui aurait pu aggraver l'incident et ne s'est pas
> produit ? Un incident survenu en heures ouvrees, un cache encore chaud, une
> dependance qui n'a pas cede. Chaque reponse designe une fragilite non traitee.

> **Post-mortem sans blame.** Decrivez les decisions avec l'information
> disponible au moment des faits, pas avec le recul. On ne cherche pas un
> responsable, mais un systeme qui a permis l'erreur.

Passez le statut a *Final* quand votre analyse est complete.

**Livrable** : Post-mortem complété + MTTR calculé

---

## Exercice 5 : Réduction du Toil

**Durée** : 45 min  
**Objectif** : Identifier et automatiser le toil

### 5.1 Identifier le toil

Dans l'Operations Console, onglet "Automation" :

1. Listez les tâches répétitives identifiées
2. Pour chaque tâche, notez :
   - Fréquence (par jour/semaine)
   - Temps manuel estimé
   - Est-ce automatisable ? (oui/partiellement/non)

### 5.2 Prioriser

Calculez le score de priorité :

```
Score = Fréquence × Temps × Automatisabilité
```

Les taches de l'onglet Automation sont declenchees par incident. Convertissez
leur frequence en occurrences par semaine a partir du nombre d'incidents
observes, puis remplissez :

| Tâche | Fréquence | Temps | Auto (0-1) | Score |
|-------|-----------|-------|------------|-------|
| Notification des stakeholders | ? /semaine | 10 min | ? | ? |
| Vérification des logs après incident | ? /semaine | ? min | ? | ? |
| ... | ... | ... | ... | ... |

### 5.3 Automatiser

Choisissez la tâche avec le score le plus élevé et écrivez un script :

**Exemple : Health check automatique**

```bash
#!/bin/bash
# health_monitor.sh

declare -A PORTS=(
    [catalog]=8081
    [cart]=8082
    [orders]=8083
    [payment]=8084
    [users]=8085
)

for service in "${!PORTS[@]}"; do
    url="http://localhost:${PORTS[$service]}/health"

    if ! curl --silent --fail "$url" > /dev/null; then
        echo "$(date) - $service unhealthy, restarting..."
        docker compose restart "${service}-service"
    fi
done
```

### 5.4 Mesurer l'impact

Après automatisation, calculez :
- Temps gagné par semaine
- Réduction du toil (%)

**Livrable** : Script d'automatisation + estimation temps gagné

---

## Exercice 6 : Synthèse et présentation

**Durée** : 30 min  
**Objectif** : Synthétiser les apprentissages

### 6.1 Préparer un rapport d'audit

Créez un document contenant :

1. **État des lieux**
   - Architecture actuelle
   - Points forts
   - Points faibles

2. **SLOs proposés**
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

### 6.2 Recommandations

Proposez 5 améliorations prioritaires :

| # | Amélioration | Impact | Effort | Priorité |
|---|--------------|--------|--------|----------|
| 1 | ? | Haut/Moyen/Bas | H/M/B | P1-P4 |
| 2 | ? | ? | ? | ? |
| ... | ... | ... | ... | ... |

**Livrable** : Rapport d'audit complet

---

## Livrables attendus

| Exercice | Livrable |
|----------|----------|
| 1. Architecture | Tableau des microservices complété |
| 2. Observabilité | Dashboard "Reskilling Overview" complété et fonctionnel |
| 3. SLOs | Tableau de SLOs justifiés + fichier de règles d'alerte |
| 4. Incident | Post-mortem complet avec MTTR calculé |
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
