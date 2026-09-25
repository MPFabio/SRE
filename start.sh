#!/bin/bash
# =============================================================================
# SRE Lab - Script de démarrage
# =============================================================================

set -o errexit

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Reskilling SRE Lab - E-Commerce Microservices"
echo "========================================"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Vérification de Docker
if ! command -v docker &> /dev/null; then
    printf "${RED}Erreur: Docker n'est pas installe${NC}\n"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    printf "${RED}Erreur: Docker Compose n'est pas installe${NC}\n"
    exit 1
fi

# Détection de la commande docker compose
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

printf "${BLUE}Construction des images...${NC}\n"
$DOCKER_COMPOSE build

printf "${BLUE}Demarrage des services...${NC}\n"
$DOCKER_COMPOSE up --detach

echo ""
printf "${GREEN}Lab SRE demarre avec succes${NC}\n"
echo ""
echo "Interfaces disponibles:"
echo "  - E-Commerce Frontend:  http://localhost:8080"
echo "  - Lab Controller:       http://localhost:8090"
echo "  - Grafana:              http://localhost:3000 (admin/admin)"
echo "  - Prometheus:           http://localhost:9090"
echo "  - Alertmanager:         http://localhost:9093"
echo "  - Locust (Traffic):     http://localhost:8089"
echo ""
echo "Microservices:"
echo "  - API Gateway:     http://localhost:8080/api/docs"
echo "  - Catalog Service: http://localhost:8081"
echo "  - Cart Service:    http://localhost:8082"
echo "  - Orders Service:  http://localhost:8083"
echo "  - Payment Service: http://localhost:8084"
echo "  - Users Service:   http://localhost:8085"
echo ""
printf "${YELLOW}Pour declencher un incident:${NC}\n"
echo "   Ouvrez http://localhost:8090 et cliquez sur un scenario"
echo ""
printf "${YELLOW}Pour voir les logs:${NC}\n"
echo "   $DOCKER_COMPOSE logs -f [service-name]"
echo ""
printf "${YELLOW}Pour arreter:${NC}\n"
echo "   ./stop.sh ou $DOCKER_COMPOSE down"
