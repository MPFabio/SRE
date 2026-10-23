#!/bin/bash
# Provoque une panne réelle dans votre namespace.
# Usage : chaos/inject.sh [scenario] [cible]
#   scenario : arret, memoire, image, port, base, cache,
#              ou rien pour une panne au hasard sur la cible
#   cible    : deployment visé (reviews-service par défaut)
set -euo pipefail

SCENARIOS=(arret memoire image port base cache)
SUR_LA_CIBLE=(arret memoire image port)
SCENARIO=${1:-${SUR_LA_CIBLE[RANDOM % ${#SUR_LA_CIBLE[@]}]}}
CIBLE=${2:-reviews-service}
SAUVEGARDE=${CHAOS_DIR:-$HOME/.chaos-reskilling}
NS=()
[ -n "${STAGIAIRE:-}" ] && NS=(--namespace "$STAGIAIRE")
k() { kubectl "${NS[@]}" "$@"; }

if [ -e "$SAUVEGARDE/panne" ]; then
    echo "Une panne est déjà en cours. Réparez-la, ou lancez chaos/rollback.sh, avant d'en provoquer une autre."
    exit 1
fi

# Bascule le déploiement en Recreate : l'ancien pod s'arrête, la panne se voit.
recreate='{"op":"replace","path":"/spec/strategy","value":{"type":"Recreate"}}'

case $SCENARIO in
    base|cache)
        [ "$SCENARIO" = base ] && CIBLE=statefulset/postgres || CIBLE=deployment/redis
        mkdir -p "$SAUVEGARDE"
        k get "$CIBLE" -o jsonpath='{.spec.replicas}' > "$SAUVEGARDE/replicas"
        k scale "$CIBLE" --replicas=0 > /dev/null
        ;;
    arret|memoire|image|port)
        k get deployment "$CIBLE" > /dev/null || {
            echo "Deployment $CIBLE introuvable. Précisez la cible : chaos/inject.sh $SCENARIO <nom>"
            exit 1
        }
        mkdir -p "$SAUVEGARDE"
        k get deployment "$CIBLE" -o jsonpath='{.spec}' > "$SAUVEGARDE/spec.json"
        case $SCENARIO in
            arret)
                k scale deployment "$CIBLE" --replicas=0 > /dev/null ;;
            memoire)
                k patch deployment "$CIBLE" --type json -p "[$recreate,
                    {\"op\":\"replace\",\"path\":\"/spec/template/spec/containers/0/resources\",
                     \"value\":{\"requests\":{\"memory\":\"2Mi\",\"cpu\":\"20m\"},\"limits\":{\"memory\":\"2Mi\",\"cpu\":\"1\"}}}]" > /dev/null ;;
            image)
                image=$(k get deployment "$CIBLE" -o jsonpath='{.spec.template.spec.containers[0].image}')
                k patch deployment "$CIBLE" --type json -p "[$recreate,
                    {\"op\":\"replace\",\"path\":\"/spec/template/spec/containers/0/image\",
                     \"value\":\"${image%:*}:version-inexistante\"}]" > /dev/null ;;
            port)
                k patch deployment "$CIBLE" --type json -p "[$recreate]" > /dev/null
                k set env deployment/"$CIBLE" PORT=9999 > /dev/null ;;
        esac
        ;;
    *)
        echo "Scénario inconnu : $SCENARIO (choix : ${SCENARIOS[*]})"
        exit 1
        ;;
esac

echo "$SCENARIO $CIBLE" > "$SAUVEGARDE/panne"
echo "Panne déclenchée $(date '+à %H:%M:%S'). Notez l'heure, puis à vous de diagnostiquer."
