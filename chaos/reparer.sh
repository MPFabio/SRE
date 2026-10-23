#!/bin/bash
# Annule la panne provoquée par chaos/lancer.sh, en remettant l'état sauvegardé.
# À utiliser si vous êtes bloqué, ou pour vérifier votre propre correction.
set -euo pipefail

SAUVEGARDE=${CHAOS_DIR:-$HOME/.chaos-lab}
NS=()
[ -n "${STAGIAIRE:-}" ] && NS=(--namespace "$STAGIAIRE")
k() { kubectl "${NS[@]}" "$@"; }

if [ ! -e "$SAUVEGARDE/panne" ]; then
    echo "Aucune panne en cours."
    exit 0
fi
read -r SCENARIO CIBLE < "$SAUVEGARDE/panne"

if [ "$SCENARIO" = base ] || [ "$SCENARIO" = cache ]; then
    k scale "$CIBLE" --replicas="$(cat "$SAUVEGARDE/replicas")" > /dev/null
    k rollout status "$CIBLE" --timeout 180s
else
    k patch deployment "$CIBLE" --type merge -p "{\"spec\": $(cat "$SAUVEGARDE/spec.json")}" > /dev/null
    k rollout status deployment/"$CIBLE" --timeout 180s
fi

rm -rf "$SAUVEGARDE"
echo "Panne \"$SCENARIO\" annulée sur $CIBLE."
