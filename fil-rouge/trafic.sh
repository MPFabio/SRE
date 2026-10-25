#!/bin/bash
# Envoie des avis au module d'exemple pendant quelques minutes, pour alimenter
# métriques, dashboards et traces.
# Usage : bash fil-rouge/trafic.sh [service] [durée en secondes]
set -euo pipefail

SERVICE=${1:-reviews-service}
DUREE=${2:-600}
NS=()
[ -n "${STAGIAIRE:-}" ] && NS=(--namespace "$STAGIAIRE")
PORT=$(kubectl "${NS[@]}" get service "$SERVICE" -o jsonpath='{.spec.ports[0].port}')

echo "Trafic vers $SERVICE:$PORT pendant $DUREE s (Ctrl+C pour arrêter)."

# Le script tourne dans le pod de la gateway, qui a Python et httpx.
kubectl "${NS[@]}" exec deploy/api-gateway -- python -c "
import random, time, httpx
url = 'http://$SERVICE:$PORT/api/reviews'
comments = ['super produit', 'livraison rapide', 'conforme', 'bof', 'déçu', 'nul', 'une arnaque']
fin = time.time() + $DUREE
envoyes = 0
while time.time() < fin:
    produit = random.randint(1, 18)
    try:
        if random.random() < 0.7:
            httpx.post(f'{url}/{produit}', timeout=5,
                       json={'rating': random.choices([1, 2, 3, 4, 5], [1, 1, 2, 4, 5])[0],
                             'comment': random.choice(comments)})
        else:
            httpx.get(f'{url}/{produit}', timeout=5)
        envoyes += 1
        if envoyes % 50 == 0:
            print(envoyes, 'requêtes envoyées', flush=True)
    except httpx.HTTPError as exc:
        print('erreur :', exc, flush=True)
    time.sleep(random.uniform(0.2, 0.8))
"
