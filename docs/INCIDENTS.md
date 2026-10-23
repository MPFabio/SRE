# Guide Incidents et Post-Mortems - Reskilling SRE

Ce guide détaille le workflow de gestion d'incidents et la rédaction de post-mortems.

## Operations Console

L'Operations Console (http://localhost:8090) est l'interface centrale pour :
- Déclencher des incidents simulés
- Suivre les incidents en cours
- Gérer les post-mortems
- Identifier le toil

## Scénarios d'incidents disponibles

### 1. Payment Service Latency (P1)

**Déclencheur** : Ajoute 2-5 secondes de latence artificielle au service de paiement.

**Impact utilisateur** :
- Checkouts extrêmement lents
- Timeouts possibles
- Circuit breaker peut s'ouvrir → échecs de paiement

**Signaux à observer** :
- Prometheus : `histogram_quantile(0.99, sum by (le) (rate(payment_request_duration_seconds_bucket[1m])))`
- Loki : `{job="payment-service"} |~ "(?i)(slow|timeout|error)"`
- Tempo : Traces avec spans payment > 2s

**Résolution** : Via l'Operations Console (*Mark Resolved*)

### 2. Catalog Service Errors (P2)

**Déclencheur** : Injecte 30% d'erreurs 500 dans le service catalog.

**Impact utilisateur** :
- Produits qui ne s'affichent pas
- Pages partiellement chargées
- Expérience dégradée

**Signaux à observer** :
- Prometheus : `sum(rate(catalog_requests_total{status="500"}[1m]))`
- Loki : `{job="catalog-service"} |~ " 500 |(?i)error"`
- Grafana : Dashboard avec taux d'erreur > 30%

**Résolution** : Via l'Operations Console (*Mark Resolved*)

### 3. Database Saturation (P1)

**Déclencheur** : Sature le pool de connexions PostgreSQL des services
persistants (catalog, orders, users).

**Impact utilisateur** :
- Latence en hausse sur la navigation produits et le parcours de commande
- Erreurs 500 quand le pool ne rend plus de connexion
- La boutique reste affichée : le panier est sur Redis, donc la panne est
  **partielle**, ce qui la rend plus difficile à diagnostiquer

**Signaux à observer** :
- Prometheus : `db_pool_idle` à zéro, `db_query_duration_seconds` en hausse
- `/ready` renvoie 503 sur les services concernés (`/health` reste à 200)
- Loki : erreurs de pool et de timeout
- Tempo : spans `db.*` qui dominent la durée totale

**Résolution** : Via l'Operations Console (*Mark Resolved*)

**Runbook détaillé** : [database-saturation.md](runbooks/database-saturation.md)

### 4. Cart Service OOMKilled (P2)

**Déclencheur** : Simule un crash du service cart par manque de mémoire.

**Impact utilisateur** :
- Impossible d'ajouter au panier
- Panier perdu
- Conversion bloquée

**Signaux à observer** :
- Prometheus : `up{job="cart-service"} == 0`
- Loki : `{job="cart-service"} |= "OOMKilled"`
- Kubernetes : `kubectl get pods -l app=cart-service`

**Résolution** : `kubectl rollout restart deployment/cart-service`

### 5. Authentication Failures (P1)

**Déclencheur** : Fait échouer 90% des authentifications.

**Impact utilisateur** :
- Impossible de se connecter
- Impossible de passer commande
- Site inutilisable pour les utilisateurs authentifiés

**Signaux à observer** :
- Prometheus : `rate(users_login_attempts_total{result="wrong_password"}[1m])`
- Loki : `{job="users-service"} |~ " 401 "`
- Tempo : Traces avec erreurs 401

**Résolution** : Via Operations Console

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

L'Operations Console génère automatiquement un template avec :

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

L'Operations Console génère automatiquement des "rapports de témoins" simulés lors du déclenchement d'un incident. Ces rapports contiennent :

- Observations de différents rôles (Dev, Ops, Support)
- Timestamps des actions
- Captures des métriques/logs

Ces rapports servent de base pour reconstruire la timeline du post-mortem.

## Identification du Toil

### Qu'est-ce que le Toil ?

Le toil est un travail :
- **Manuel** : Nécessite une intervention humaine
- **Répétitif** : Se produit régulièrement
- **Automatisable** : Peut être scripté
- **Tactique** : Sans valeur durable
- **Scalant** : Augmente avec la charge

### Toil identifié dans l'application fil rouge

L'Operations Console (onglet "Automation") identifie automatiquement :

| Tâche | Fréquence | Temps/occurrence |
|-------|-----------|------------------|
| Restart pods crashés | 5x/jour | 5 min |
| Vérification logs | 10x/jour | 2 min |
| Reset circuit breaker | 3x/jour | 3 min |
| Collecte métriques manuelles | 2x/jour | 10 min |
| Notification stakeholders | Par incident | 15 min |

### Priorisation

**Score de priorité** = Fréquence × Temps × Facilité d'automatisation

Exemple :
- Restart pods : 5 × 5 × 0.9 = 22.5 → Haute priorité
- Notification : 0.5 × 15 × 0.7 = 5.25 → Moyenne priorité

### Automatisation

Pour chaque toil identifié, l'Operations Console suggère :
- Script d'automatisation
- Estimation du temps gagné
- Complexité d'implémentation

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
