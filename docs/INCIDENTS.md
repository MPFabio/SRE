# Guide Incidents et Post-Mortems - Reskilling SRE

Ce guide détaille le workflow de gestion d'incidents et la rédaction de post-mortems.

## Operations Console

L'Operations Console (http://localhost:8090) est l'interface centrale pour :
- Déclencher des incidents simulés
- Suivre les incidents en cours
- Gérer les post-mortems
- Identifier le toil

## Scénarios d'incidents disponibles

Chaque scénario est livré avec des témoignages fictifs. Ils donnent des
pistes, pas des faits : confrontez-les aux métriques, certains se trompent.

### 1. Latence élevée du service de paiement (P1)

**Déclencheur** : ajoute 3 secondes à l'appel au prestataire de paiement externe.

**Impact utilisateur** :
- Chaque achat prend plus de 3 secondes
- La navigation et le panier ne sont pas touchés

**Signaux à observer** :
- Prometheus : `histogram_quantile(0.99, sum by (le) (rate(payment_request_duration_seconds_bucket{endpoint="/api/payments"}[1m])))`
- Alertes : `PaymentServiceHighLatency`, `HighLatencyP99Orders`
- Loki : `{job="payment-service"} |~ "(?i)(slow|timeout|error)"`
- Tempo : traces dont le span `process_payment` dépasse 3 s
- Le circuit breaker reste fermé : il ne s'ouvre que sur des erreurs

**Résolution** : Via l'Operations Console (*Mark Resolved*)

### 2. Erreurs 500 sur le service Catalogue (P2)

**Déclencheur** : 30 % d'erreurs 500 sur catalog-service.

**Impact utilisateur** :
- Produits qui ne s'affichent pas
- Pages partiellement chargées
- Expérience dégradée

**Signaux à observer** :
- Prometheus : `sum(rate(catalog_requests_total{status="500"}[1m]))`
- Alertes : `HighErrorRate`, `CriticalErrorRate` sur catalog
- Loki : `{job="catalog-service"} |~ " 500 |(?i)error"`
- Grafana : disponibilité en baisse sur *SRE Overview*

**Résolution** : Via l'Operations Console (*Mark Resolved*)

### 3. Saturation de la base de données (P1)

**Déclencheur** : simule une base surchargée, vue depuis catalog-service :
+2 s sur chaque requête et 20 % d'erreurs 500.

**Impact utilisateur** :
- Navigation produits lente, erreurs intermittentes
- Ajout au panier et commande ralentis : cart et orders interrogent catalog
- La boutique reste affichée : la panne est **partielle**, ce qui la rend
  plus difficile à diagnostiquer

**Signaux à observer** :
- Alertes : `CriticalLatencyP99`, `HighErrorRate` et `CriticalErrorRate` sur catalog
- Prometheus : `histogram_quantile(0.99, sum by (le) (rate(catalog_request_duration_seconds_bucket[5m])))`
- Tempo : les spans de catalog-service durent plus de 2 s
- Côté base, `db_pool_idle`, `db_query_duration_seconds` et
  `pg_stat_database_numbackends` restent normaux : les témoignages (CPU à
  98 %, I/O saturées) ne sont pas confirmés par les métriques

**Résolution** : Via l'Operations Console (*Mark Resolved*)

**Runbook** : [database-saturation.md](runbooks/database-saturation.md), pour
vérifier l'état réel du pool et de la base.

### 4. Service Panier indisponible (P2)

**Déclencheur** : 80 % d'erreurs 500 sur cart-service.

**Impact utilisateur** :
- Ajouts au panier et consultation du panier en échec la plupart du temps
- Commandes refusées : orders ne parvient pas à lire le panier et répond
  « panier vide » (400)

**Signaux à observer** :
- Prometheus : `sum by (status) (rate(cart_requests_total[1m]))`
- Alertes : `HighErrorRate`, `CriticalErrorRate` sur cart
- Loki : `{job="cart-service"} |= "Unhandled exception"`
- Kubernetes : le pod reste `Running` et prêt. Le témoignage qui parle
  d'OOMKilled ne résiste pas à `kubectl get pods -l app=cart-service`

**Résolution** : Via l'Operations Console (*Mark Resolved*)

### 5. Échecs d'authentification utilisateurs (P1)

**Déclencheur** : 90 % d'erreurs 500 sur users-service.

**Impact utilisateur** :
- Connexion et pages de compte en échec
- La boutique n'a pas de compte client : navigation, panier et commandes
  ne sont pas touchés

**Signaux à observer** :
- Prometheus : `sum by (status) (rate(users_requests_total[1m]))`
- Alertes : `HighErrorRate`, `CriticalErrorRate` sur users
- Loki : `{job="users-service"} |~ " 500 "`

**Résolution** : Via l'Operations Console (*Mark Resolved*)

## Workflow d'incident

### Phase 1 : Détection (T+0)

**Sources de détection** :
1. Alerte Alertmanager
2. Monitoring Grafana
3. Signalement utilisateur
4. Operations Console

**Actions immédiates** :
- Confirmer l'incident
- Évaluer la sévérité (P1-P4)
- Notifier les parties prenantes

### Phase 2 : Triage (T+5min)

**Classification** :

| Priorité | Impact | Exemples | SLA |
|----------|--------|----------|-----|
| P1 | Critique - Service indisponible | Auth down, paiements KO | 15 min |
| P2 | Majeur - Fonctionnalité dégradée | Catalog errors, cart slow | 1h |
| P3 | Mineur - Impact limité | Logs manquants | 4h |
| P4 | Cosmétique | UI glitch | 24h |

**Questions clés** :
- Combien d'utilisateurs impactés ?
- Quelles fonctionnalités touchées ?
- Y a-t-il une perte de données ?
- Le problème empire-t-il ?

### Phase 3 : Investigation (T+10min)

**Checklist d'investigation** :

1. **Métriques (Prometheus/Grafana)**
   - [ ] Identifier le service en cause
   - [ ] Quantifier l'impact (% erreurs, latence)
   - [ ] Vérifier si d'autres services sont impactés
   - [ ] Corréler avec des déploiements récents

2. **Logs (Loki)**
   - [ ] Rechercher les erreurs dans le service impacté
   - [ ] Identifier le pattern d'erreur
   - [ ] Trouver le premier log d'erreur
   - [ ] Vérifier les logs des dépendances

3. **Traces (Tempo)**
   - [ ] Analyser une requête en erreur
   - [ ] Identifier le span problématique
   - [ ] Mesurer les temps de réponse

**Template de notes d'investigation** :

```markdown
## Incident: [Nom]
**Début**: [Timestamp]
**Sévérité**: P[1-4]
**Service(s)**: [Liste]

### Timeline
- HH:MM - [Observation]
- HH:MM - [Action]

### Métriques clés
- Taux d'erreur: X%
- Latence P99: Xs
- Requêtes impactées: N

### Logs pertinents
[Copier les logs clés]

### Hypothèses
1. [Hypothèse 1] - [Validé/Invalidé]
2. [Hypothèse 2] - [Validé/Invalidé]

### Cause racine identifiée
[Description]
```

### Phase 4 : Résolution (Variable)

**Actions de résolution** :

1. **Mitigation immédiate** (si possible)
   - Rollback
   - Feature flag
   - Scale up
   - Restart

2. **Fix permanent**
   - Code fix
   - Configuration change
   - Infrastructure change

3. **Validation**
   - Métriques revenues à la normale
   - Logs sans erreurs
   - Tests manuels OK

### Phase 5 : Post-Mortem (T+24-48h)

## Rédaction du Post-Mortem

### Principes

1. **Blameless** : Pas de blâme individuel
2. **Factuel** : Basé sur des données
3. **Constructif** : Focus sur les améliorations
4. **Partagé** : Accessible à toute l'équipe

### Structure du Post-Mortem

L'Operations Console génère un squelette : impact, durée, services
touchés, timeline, participants et pistes des témoins. Le reste est à
rédiger (voir le bonus 3.5). Un post-mortem complet suit cette structure :

#### 1. Résumé exécutif
- Date et durée de l'incident
- Impact (utilisateurs, revenus, SLO)
- Cause racine (1 phrase)
- Résolution (1 phrase)

#### 2. Timeline détaillée

```markdown
| Heure | Événement | Source |
|-------|-----------|--------|
| 14:00 | Déploiement v2.3.1 | CI/CD |
| 14:15 | Première alerte latence | Alertmanager |
| 14:17 | Incident déclaré P1 | On-call |
| 14:25 | Cause identifiée | Investigation |
| 14:30 | Rollback initié | Mitigation |
| 14:35 | Service rétabli | Monitoring |
```

#### 3. Impact

- **Utilisateurs impactés** : X (Y%)
- **Durée** : Xmin
- **Revenus perdus** : €X (estimation)
- **SLO consommé** : X% du budget mensuel

#### 4. Cause racine

Description technique de ce qui s'est passé :
- Qu'est-ce qui a déclenché le problème ?
- Pourquoi les protections n'ont pas fonctionné ?
- Quels facteurs ont contribué ?

#### 5. Leçons apprises

**Ce qui a bien fonctionné** :
- Détection rapide via alerting
- Communication efficace
- Rollback fonctionnel

**Ce qui peut être amélioré** :
- Monitoring de la métrique X
- Tests de charge
- Documentation du runbook

#### 6. Action Items

| Action | Priorité | Responsable | Deadline |
|--------|----------|-------------|----------|
| Ajouter alerte sur métrique X | P1 | @alice | J+7 |
| Améliorer tests de charge | P2 | @bob | J+14 |
| Documenter le runbook | P3 | @charlie | J+30 |

### Rapports de témoins

L'Operations Console génère des "rapports de témoins" simulés lors du déclenchement d'un incident. Chaque rapport contient :

- L'observation d'un rôle (développeur, SRE, DBA, DevOps)
- Une chronologie de ce qu'il a vu et fait
- La cause qu'il soupçonne et les actions qu'il a menées

Ces rapports aident à reconstruire la timeline du post-mortem, mais ils ne
disent pas toujours vrai : vérifiez chaque affirmation dans les métriques,
les logs et les traces.

## Identification du Toil

### Qu'est-ce que le Toil ?

Le toil est un travail :
- **Manuel** : Nécessite une intervention humaine
- **Répétitif** : Se produit régulièrement
- **Automatisable** : Peut être scripté
- **Tactique** : Sans valeur durable
- **Scalant** : Augmente avec la charge

### Toil identifié dans l'application fil rouge

L'Operations Console (onglet "Automation") liste cinq tâches, toutes
répétées à chaque incident :

| Tâche | Fréquence | Temps/occurrence |
|-------|-----------|------------------|
| Restart manuel des pods en CrashLoopBackOff | Par incident | 15 min |
| Vérification manuelle des logs après incident | Par incident | 30 min |
| Reset manuel du circuit breaker | Par incident | 5 min |
| Collecte des métriques pour le post-mortem | Par incident | 20 min |
| Notification des stakeholders | Par incident | 10 min |

### Priorisation

**Score de priorité** = Fréquence × Temps × Facilité d'automatisation

Exemple avec 3 incidents par semaine :
- Collecte des métriques : 3 × 20 × 0.9 = 54 → Haute priorité
- Reset du circuit breaker : 3 × 5 × 1 = 15 → Basse priorité

### Automatisation

Pour chaque tâche, l'Operations Console propose une piste
d'automatisation. Le bouton **Automate** la marque comme automatisée et
calcule le temps gagné sur les incidents passés.

## Métriques SRE

### MTTR (Mean Time To Recovery)

```
MTTR = Temps total de downtime / Nombre d'incidents
```

Objectif typique : < 30 min pour P1

### MTTD (Mean Time To Detect)

```
MTTD = Temps entre début incident et première alerte
```

Objectif typique : < 5 min

### Change Failure Rate

```
CFR = Déploiements causant incidents / Total déploiements
```

Objectif typique : < 15%

### Toil Budget

```
Temps toil / Temps total équipe < 50%
```

Idéalement < 30% pour permettre le travail d'engineering.
