# Scripts de chaos : provoquer, diagnostiquer, corriger

Ces scripts cassent réellement quelque chose dans votre namespace : rien
n'est simulé. À vous de trouver ce qui ne va pas avec vos dashboards, vos
alertes, vos logs et vos traces, puis de le corriger.

Les incidents de l'Operations Console (bonus 3) sont différents : ils
injectent des pannes dans le code, et se résolvent d'un clic.

## Lancer une panne

Sur `utils-stagiaireXX`, depuis la racine du repo :

```bash
bash chaos/lancer.sh                 # une panne au hasard sur votre module
bash chaos/lancer.sh memoire         # une panne précise
bash chaos/lancer.sh port catalog-service   # une panne sur un autre service
```

La cible par défaut est `reviews-service`. Si votre module porte un autre
nom, passez-le en second argument. Une seule panne à la fois.

Le script affiche l'heure de la panne : notez-la, elle sert à mesurer
votre délai de détection et de réparation. Ne lisez pas le script avant
d'avoir trouvé : il donne la réponse.

| Scénario | Ce que vous allez constater |
|---|---|
| `arret` | Le service ne répond plus |
| `memoire` | Le service ne démarre plus |
| `image` | Le service ne démarre plus |
| `port` | Le service démarre mais n'est jamais prêt |
| `base` | Plusieurs services CapShop tombent en même temps |
| `cache` | Le panier ne fonctionne plus |

## Diagnostiquer

Partez des symptômes, comme en production :

1. **Alertes** : http://localhost:9093 ou http://localhost:9090/alerts.
   Quelle alerte, sur quel service, depuis quand ?
2. **Dashboards** : Grafana, votre dashboard et *SRE Overview*. Le trafic,
   les erreurs, la latence ont-ils changé ? Pour quels services ?
3. **Traces** : Tempo. Une requête vers le service en panne échoue-t-elle,
   et à quelle étape ?
4. **Kubernetes** : l'état réel des pods.

```bash
kubectl get pods
kubectl describe pod -l app=<service>        # section Events, en bas
kubectl logs deploy/<service> --tail 50
kubectl logs deploy/<service> --previous     # logs du container précédent, s'il a redémarré
kubectl get events --sort-by=.lastTimestamp | tail -20
kubectl rollout history deployment/<service>
```

## Corriger

Corrigez avec `kubectl` (`scale`, `set image`, `set resources`, `set env`,
`rollout undo`...) puis vérifiez que les alertes repassent au vert.

Bloqué ? `bash chaos/reparer.sh` remet le service dans l'état d'avant la
panne. Lancez-le aussi après votre propre correction : il nettoie la
sauvegarde et permet de lancer la panne suivante.

## Pistes et solutions

<details>
<summary><code>arret</code> : pistes</summary>

- `ServiceDown` et `EndpointDown` se déclenchent sur le service.
- `kubectl get pods -l app=<service>` ne renvoie rien. Il n'y a pas de pod
  en erreur : il n'y a plus de pod du tout.
- Combien de replicas le Deployment demande-t-il ?
  `kubectl get deployment <service>`

</details>

<details>
<summary><code>arret</code> : solution</summary>

Le Deployment a été ramené à 0 replica : personne ne l'a cassé, quelqu'un
l'a arrêté.

```bash
kubectl scale deployment <service> --replicas=1
```

À retenir : regardez ce que le système *demande* (`spec.replicas`) avant
de chercher ce qui a planté.

</details>

<details>
<summary><code>memoire</code> : pistes</summary>

- Le pod est en `RunContainerError` ou `CrashLoopBackOff`, et le nombre de
  redémarrages augmente.
- `kubectl logs` ne montre rien : le programme n'a même pas démarré.
- La section *Events* de `kubectl describe pod` contient la raison exacte.
- Comparez les ressources demandées avec celles des autres services.

</details>

<details>
<summary><code>memoire</code> : solution</summary>

La limite mémoire a été abaissée à 2 Mi. Le container est tué avant même
de démarrer : `container init was OOM-killed (memory limit too low?)`.
Avec une limite un peu plus haute, on verrait `OOMKilled` dans
`lastState` après chaque démarrage.

```bash
kubectl set resources deployment/<service> \
    --requests=memory=80Mi --limits=memory=256Mi
```

Le Deployment a aussi été passé en stratégie `Recreate` : l'ancien pod a
été arrêté avant que le nouveau démarre. Avec la stratégie par défaut
(`RollingUpdate`), l'ancien pod aurait continué à servir, et la panne
n'aurait bloqué que le déploiement. Remettez-la :

```bash
kubectl patch deployment <service> --type merge \
    -p '{"spec":{"strategy":{"type":"RollingUpdate"}}}'
```

</details>

<details>
<summary><code>image</code> : pistes</summary>

- Le pod est en `ErrImagePull` puis `ImagePullBackOff`.
- Quelle image le pod essaie-t-il de télécharger ?
  `kubectl describe pod -l app=<service>`
- Cette version existe-t-elle sur le registry ?
- `kubectl rollout history deployment/<service>` montre les versions
  précédentes.

</details>

<details>
<summary><code>image</code> : solution</summary>

Le Deployment pointe vers un tag d'image qui n'existe pas
(`version-inexistante`). C'est la panne d'un déploiement raté : faute de
frappe dans le tag, image jamais poussée, registry inaccessible.

```bash
kubectl rollout undo deployment/<service>
```

ou `kubectl set image deployment/<service> '*'=<image correcte>`. Pensez
aussi à remettre la stratégie `RollingUpdate` (voir `memoire`) : c'est
elle qui, en temps normal, évite qu'une mauvaise image coupe le service.

</details>

<details>
<summary><code>port</code> : pistes</summary>

- Le pod est `Running` mais `0/1` : il n'est jamais prêt, et finit par
  redémarrer.
- *Events* : `Readiness probe failed` et `Liveness probe failed`, avec
  `connection refused`.
- Les logs du programme indiquent sur quel port il écoute. Est-ce celui
  que Kubernetes interroge ?
- `kubectl get deployment <service> -o yaml`, cherchez `PORT`.

</details>

<details>
<summary><code>port</code> : solution</summary>

La variable `PORT` vaut 9999 : le programme écoute sur 9999, mais les
probes et le Service visent 8086. Le programme fonctionne, personne ne
peut le joindre.

```bash
kubectl set env deployment/<service> PORT=8086
```

Puis remettez la stratégie `RollingUpdate` (voir `memoire`). À retenir :
un pod `Running` n'est pas un pod qui fonctionne, c'est la readiness qui
le dit.

</details>

<details>
<summary><code>base</code> : pistes</summary>

- Plusieurs alertes en même temps, sur plusieurs services : cherchez ce
  qu'ils ont en commun plutôt que de les traiter un par un.
- `DatabaseDown` (`pg_up == 0`) est-elle déclenchée ?
- Quels services sont `0/1` ? Lesquels restent prêts (cart, payment) ?
- Les traces de la gateway vers catalog échouent en 503 ou 504.

</details>

<details>
<summary><code>base</code> : solution</summary>

PostgreSQL a été arrêté (StatefulSet à 0 replica). Catalog, orders et
users dépendent de la base : leur readiness échoue, la gateway renvoie
des 503. Cart et payment n'en dépendent pas et restent prêts.

```bash
kubectl scale statefulset postgres --replicas=1
```

Les services se reconnectent seuls en une minute environ. À retenir :
quand tout tombe en même temps, la cause est souvent une dépendance
commune. Redémarrer les services un par un n'aurait rien réparé (voir le
bonus 5.3).

</details>

<details>
<summary><code>cache</code> : pistes</summary>

- `ServiceDown` et `EndpointDown` sur `cart-service`, alors que le pod est
  `Running` : il n'est simplement pas prêt (`0/1`).
- La gateway renvoie des 503 sur `/api/cart/...`.
- Que vérifie la readiness de cart ? `kubectl exec deploy/api-gateway --
  curl --silent cart-service:8082/ready`
- Les logs de cart parlent d'une dépendance.

</details>

<details>
<summary><code>cache</code> : solution</summary>

Redis, où sont stockés les paniers, a été arrêté (Deployment à 0
replica). Cart ne peut plus lire ni écrire de panier : sa readiness
échoue, Kubernetes le retire du Service, et la gateway répond 503.

```bash
kubectl scale deployment redis --replicas=1
```

Cart redevient prêt de lui-même, sans redémarrage. Les paniers en cours
sont perdus : Redis tourne ici sans persistance.

</details>

## Mesurer

Pour chaque panne, notez :

| | Heure |
|---|---|
| Panne déclenchée | affichée par le script |
| Première alerte | Alertmanager |
| Cause identifiée | vous |
| Service rétabli | alertes au vert |

Délai de détection = première alerte − panne. MTTR = rétablissement −
panne. Quelle étape vous a pris le plus de temps, et quel outil vous a
mis sur la piste ?
