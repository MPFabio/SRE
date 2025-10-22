# Post-Mortem - [Nom de l'Incident]

**Date de l'incident :** [YYYY-MM-DD HH:MM]  
**Durée :** [X minutes/heures]  
**Impact :** [Description de l'impact]  
**Résolution :** [Date et heure de résolution]  
**Équipe :** [Noms des participants]

---

## Résumé Exécutif

### Impact
- **Service affecté :** [Nom du service]
- **Utilisateurs impactés :** [Nombre estimé]
- **Durée de l'indisponibilité :** [X minutes/heures]
- **Perte de revenus estimée :** [Si applicable]

### Cause Racine
[Description brève de la cause racine]

### Actions Correctives
[Liste des actions prises pour résoudre l'incident]

---

## Chronologie de l'Incident

| Heure | Action | Personne | Détails |
|-------|--------|----------|---------|
| HH:MM | Détection | [Nom] | [Description] |
| HH:MM | Investigation | [Nom] | [Description] |
| HH:MM | Mitigation | [Nom] | [Description] |
| HH:MM | Résolution | [Nom] | [Description] |

---

## Métriques de l'Incident

### SLIs Impactés
- **Disponibilité :** [X%] (SLO: 99.9%)
- **Latence P95 :** [X ms] (SLO: 500ms)
- **Latence P99 :** [X ms] (SLO: 2s)
- **Taux d'erreur :** [X%] (SLO: 0.1%)

### Error Budget
- **Consommation :** [X%]
- **Burn Rate :** [X.x]
- **Temps jusqu'à épuisement :** [X heures]

---

## Analyse de la Cause Racine

### Cause Immédiate
[Description de ce qui s'est passé directement]

### Cause Contributive
[Facteurs qui ont contribué à l'incident]

### Cause Racine
[La cause fondamentale qui a permis à l'incident de se produire]

### Méthode d'Analyse
- [ ] 5 Whys
- [ ] Fishbone Diagram
- [ ] Fault Tree Analysis
- [ ] Autre : [Préciser]

---

## 🚨 Détection et Alertes

### Comment l'incident a-t-il été détecté ?
- [ ] Monitoring automatique
- [ ] Alerte utilisateur
- [ ] Alerte équipe
- [ ] Autre : [Préciser]

### Temps de Détection
- **Détection :** [X minutes] après le début de l'incident
- **Alerte :** [X minutes] après la détection
- **Réponse :** [X minutes] après l'alerte

### Qualité des Alertes
- [ ] Alertes claires et actionables
- [ ] Trop de bruit (faux positifs)
- [ ] Alertes manquantes
- [ ] Alertes tardives

---

## ⚡ Réponse et Résolution

### Temps de Résolution
- **MTTR (Mean Time To Resolution) :** [X minutes]
- **MTBF (Mean Time Between Failures) :** [X jours]

### Actions de Mitigation
1. [Action 1]
2. [Action 2]
3. [Action 3]

### Actions de Résolution
1. [Action 1]
2. [Action 2]
3. [Action 3]

### Communication
- [ ] Page d'état mise à jour
- [ ] Communication interne
- [ ] Communication clients
- [ ] Post-mortem partagé

---

## 🎓 Leçons Apprises

### Ce qui a bien fonctionné
1. [Point positif 1]
2. [Point positif 2]
3. [Point positif 3]

### Ce qui n'a pas fonctionné
1. [Point négatif 1]
2. [Point négatif 2]
3. [Point négatif 3]

### Toil Identifié
[Liste des tâches manuelles répétitives identifiées]

---

## Actions Correctives

### Actions Immédiates (0-24h)
- [ ] [Action 1] - [Responsable] - [Échéance]
- [ ] [Action 2] - [Responsable] - [Échéance]
- [ ] [Action 3] - [Responsable] - [Échéance]

### Actions Court Terme (1-7 jours)
- [ ] [Action 1] - [Responsable] - [Échéance]
- [ ] [Action 2] - [Responsable] - [Échéance]
- [ ] [Action 3] - [Responsable] - [Échéance]

### Actions Long Terme (1-4 semaines)
- [ ] [Action 1] - [Responsable] - [Échéance]
- [ ] [Action 2] - [Responsable] - [Échéance]
- [ ] [Action 3] - [Responsable] - [Échéance]

---

## 🤖 Automatisation et Réduction du Toil

### Toil Identifié
1. **Tâche manuelle :** [Description]
   - **Fréquence :** [X fois par jour/semaine]
   - **Temps :** [X minutes]
   - **Automatisation proposée :** [Description]

2. **Tâche manuelle :** [Description]
   - **Fréquence :** [X fois par jour/semaine]
   - **Temps :** [X minutes]
   - **Automatisation proposée :** [Description]

### Scripts d'Automatisation
- [ ] [Script 1] - [Description]
- [ ] [Script 2] - [Description]
- [ ] [Script 3] - [Description]

### Métriques de Réduction du Toil
- **Temps de résolution avant :** [X minutes]
- **Temps de résolution après :** [X minutes]
- **Réduction :** [X%]

---

## Amélioration des SLOs

### SLOs Actuels
- **Disponibilité :** 99.9% (Error Budget: 0.1%)
- **Latence P95 :** 500ms
- **Latence P99 :** 2s
- **Taux d'erreur :** 0.1%

### Ajustements Proposés
- [ ] [Ajustement 1]
- [ ] [Ajustement 2]
- [ ] [Ajustement 3]

### Justification
[Explication des ajustements proposés]

---

## 🔄 Processus d'Amélioration

### Améliorations du Processus
1. [Amélioration 1]
2. [Amélioration 2]
3. [Amélioration 3]

### Formation et Documentation
- [ ] [Formation 1]
- [ ] [Documentation 1]
- [ ] [Runbook 1]

### Outils et Monitoring
- [ ] [Outil 1]
- [ ] [Métrique 1]
- [ ] [Dashboard 1]

---

## 📈 Suivi et Métriques

### KPIs de Suivi
- **MTTR :** [Cible: X minutes]
- **MTBF :** [Cible: X jours]
- **Taux de résolution automatique :** [Cible: X%]
- **Satisfaction équipe :** [Cible: X/10]

### Prochaine Révision
**Date :** [YYYY-MM-DD]  
**Responsable :** [Nom]

---

## 📝 Notes Supplémentaires

[Espace pour des notes, observations ou commentaires supplémentaires]

---

## Validation

- [ ] **Équipe SRE :** [Nom] - [Date]
- [ ] **Équipe Développement :** [Nom] - [Date]
- [ ] **Management :** [Nom] - [Date]

---

**Template créé pour le Lab SRE - Version 1.0**  
**Dernière mise à jour :** [Date]
