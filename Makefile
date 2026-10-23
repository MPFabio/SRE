.PHONY: start stop restart build logs status clean help incident-% chaos chaos-% test

# Couleurs
GREEN  := \033[0;32m
YELLOW := \033[0;33m
RED    := \033[0;31m
NC     := \033[0m

# Commande docker compose (v2 par defaut, fallback v1)
DC := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

help: ## Affiche cette aide
	@echo "$(GREEN)Reskilling SRE - Commandes disponibles$(NC)"
	@echo ""
	@grep --extended-regexp '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# =============================================================================
# Gestion de l'application fil rouge
# =============================================================================

start: ## Demarre l'application fil rouge
	@./start.sh

stop: ## Arrete l'application fil rouge
	@$(DC) down

restart: stop start ## Redemarre l'application fil rouge

build: ## Reconstruit toutes les images
	@$(DC) build

logs: ## Affiche les logs de tous les services
	@$(DC) logs --follow

status: ## Affiche le status des services
	@$(DC) ps

clean: ## Supprime tous les volumes et nettoie
	@$(DC) down --volumes
	@docker system prune --force
	@echo "$(GREEN)Nettoyage termine$(NC)"

# =============================================================================
# Logs par service
# =============================================================================

logs-gateway: ## Logs de l'API Gateway
	@$(DC) logs --follow api-gateway

logs-catalog: ## Logs du Catalog Service
	@$(DC) logs --follow catalog-service

logs-cart: ## Logs du Cart Service
	@$(DC) logs --follow cart-service

logs-orders: ## Logs du Orders Service
	@$(DC) logs --follow orders-service

logs-payment: ## Logs du Payment Service
	@$(DC) logs --follow payment-service

logs-users: ## Logs du Users Service
	@$(DC) logs --follow users-service

# =============================================================================
# Incidents
# =============================================================================

incident-payment: ## Declenche un incident Payment Latency
	@$(MAKE) --no-print-directory incident TYPE=payment_latency

incident-catalog: ## Declenche un incident Catalog Errors
	@$(MAKE) --no-print-directory incident TYPE=catalog_errors

incident-database: ## Declenche un incident Database Saturation
	@$(MAKE) --no-print-directory incident TYPE=database_saturation

incident: ## Declenche un incident (TYPE=payment_latency)
	@if [ -z "$(TYPE)" ]; then echo "$(RED)Usage: make incident TYPE=payment_latency$(NC)"; exit 1; fi
	@echo "$(RED)Declenchement incident $(TYPE)...$(NC)"
	@curl --silent --fail --request POST http://localhost:8090/api/incidents/trigger \
		--header 'Content-Type: application/json' \
		--data '{"incident_type":"$(TYPE)"}' \
		| jq '{id, title, severity, status, affected_services}'
	@echo "$(YELLOW)Observez dans Grafana: http://localhost:3000$(NC)"

incident-types: ## Liste les scenarios d'incident disponibles
	@curl --silent http://localhost:8090/api/incident-types | jq --raw-output '.[] | "\(.type)  [\(.severity)]  \(.title)"'

incident-list: ## Liste les incidents (les plus recents d'abord)
	@curl --silent http://localhost:8090/api/incidents \
		| jq --raw-output '.[-10:] | reverse | .[] | "\(.id)  \(.status)  \(.type)"'

incident-resolve: ## Resout tous les incidents actifs
	@echo "$(GREEN)Resolution des incidents actifs...$(NC)"
	@for id in $$(curl --silent http://localhost:8090/api/incidents | jq --raw-output '.[] | select(.status != "resolved") | .id'); do \
		if curl --silent --fail --request PUT "http://localhost:8090/api/incidents/$$id/status?status=resolved" > /dev/null; then \
			echo "   $$id resolu"; \
		else \
			echo "   $(RED)$$id: echec$(NC)"; \
		fi; \
	done
	@echo "$(GREEN)Termine$(NC)"


chaos: ## Injecte du chaos (SERVICE=payment LATENCY=3000 ERRORS=0.3)
	@if [ -z "$(SERVICE)" ]; then echo "$(RED)Usage: make chaos SERVICE=payment LATENCY=3000 ERRORS=0.3$(NC)"; exit 1; fi
	@if [ -z "$(CHAOS_PORT_$(SERVICE))" ]; then echo "$(RED)Service inconnu: $(SERVICE) (attendu: $(CHAOS_SERVICES))$(NC)"; exit 1; fi
	@curl --silent --fail --request POST http://localhost:$(CHAOS_PORT_$(SERVICE))/api/chaos --header 'Content-Type: application/json' --data '{"enabled":true,"latency_ms":$(or $(LATENCY),0),"error_rate":$(or $(ERRORS),0)}' && echo "" && echo "$(GREEN)Chaos actif sur $(SERVICE)$(NC)"

chaos-payment-latency: ## Ajoute 3s de latence au Payment Service
	@$(MAKE) --no-print-directory chaos SERVICE=payment LATENCY=3000

chaos-catalog-errors: ## Injecte 30% d'erreurs au Catalog Service
	@$(MAKE) --no-print-directory chaos SERVICE=catalog ERRORS=0.3

chaos-status: ## Affiche l'etat du chaos sur tous les services
	@for entry in catalog:8081 cart:8082 orders:8083 payment:8084 users:8085; do name=$${entry%%:*}; port=$${entry##*:}; printf "  %-10s " "$$name"; curl --silent --fail http://localhost:$$port/api/chaos 2>/dev/null || printf "(indisponible)"; echo ""; done

chaos-stop: ## Arrete le chaos sur tous les services
	@for entry in catalog:8081 cart:8082 orders:8083 payment:8084 users:8085; do name=$${entry%%:*}; port=$${entry##*:}; curl --silent --fail --request POST http://localhost:$$port/api/chaos --header 'Content-Type: application/json' --data '{"enabled":false,"latency_ms":0,"error_rate":0}' >/dev/null 2>&1 && echo "  $$name: chaos arrete"; done
	@echo "$(GREEN)Chaos arrete sur tous les services$(NC)"

psql: ## Ouvre un shell PostgreSQL
	@$(DC) exec postgres psql --username=capshop --dbname=capshop

db-stats: ## Statistiques de la base (lignes par table)
	@$(DC) exec postgres psql --username=capshop --dbname=capshop --command="		SELECT 'catalog.products' AS table, count(*) FROM catalog.products 		UNION ALL SELECT 'orders.orders', count(*) FROM orders.orders 		UNION ALL SELECT 'users.users', count(*) FROM users.users 		UNION ALL SELECT 'lab.incidents', count(*) FROM lab.incidents;"

# =============================================================================
# Tests
# =============================================================================

test: ## Verifie que tous les services sont operationnels
	@echo "$(YELLOW)Verification des services...$(NC)"
	@printf "API Gateway:    " && curl --silent --fail http://localhost:8080/health > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@printf "Catalog:        " && curl --silent --fail http://localhost:8081/health > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@printf "Cart:           " && curl --silent --fail http://localhost:8082/health > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@printf "Orders:         " && curl --silent --fail http://localhost:8083/health > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@printf "Payment:        " && curl --silent --fail http://localhost:8084/health > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@printf "Users:          " && curl --silent --fail http://localhost:8085/health > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@printf "Operations Console: " && curl --silent --fail http://localhost:8090/health > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@printf "Prometheus:     " && curl --silent --fail http://localhost:9090/-/healthy > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@printf "Alertmanager:   " && curl --silent --fail http://localhost:9093/-/healthy > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@printf "Grafana:        " && curl --silent --fail http://localhost:3000/api/health > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@printf "Loki:           " && $(DC) exec --no-TTY api-gateway python -c "import urllib.request;urllib.request.urlopen('http://loki:3100/ready')" >/dev/null 2>&1 && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@printf "PostgreSQL:     " && $(DC) exec --no-TTY postgres pg_isready --quiet && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@printf "Tempo:          " && $(DC) exec --no-TTY api-gateway python -c "import urllib.request;urllib.request.urlopen('http://tempo:3200/ready')" >/dev/null 2>&1 && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"

test-purchase: ## Simule un achat complet
	@echo "$(YELLOW)Simulation d'achat...$(NC)"
	@echo "1. Recuperation produits..."
	@PRODUCT=$$(curl --silent http://localhost:8080/api/products | jq '.[0]') && \
	PRICE=$$(echo $$PRODUCT | jq --raw-output '.price') && \
	echo "   Produit: $$(echo $$PRODUCT | jq --raw-output '.brand + " " + .name') ($$PRICE EUR)" && \
	echo "2. Ajout au panier..." && \
	curl --silent --fail --request POST http://localhost:8080/api/cart/user-test/items \
		--header "Content-Type: application/json" \
		--data '{"product_id": 1, "quantity": 1}' > /dev/null && \
	echo "3. Creation commande (le paiement est declenche par orders-service)..." && \
	ORDER=$$(curl --silent --request POST http://localhost:8080/api/orders \
		--header "Content-Type: application/json" \
		--data '{"user_id": "user-test", "items": [{"product_id": 1, "quantity": 1}], "shipping_address": {"street": "1 rue de Rivoli", "city": "Paris", "postal_code": "75001", "country": "FR"}}') && \
	if [ "$$(echo $$ORDER | jq --raw-output '.id // empty')" = "" ]; then \
		echo "   $(RED)Echec: $$(echo $$ORDER | jq --compact-output '.detail')$(NC)"; exit 1; fi && \
	echo "   Commande: $$(echo $$ORDER | jq --raw-output '.id')" && \
	echo "   Statut:   $$(echo $$ORDER | jq --raw-output '.status')" && \
	echo "   Total:    $$(echo $$ORDER | jq --raw-output '.total') EUR" && \
	echo "$(GREEN)Achat simule avec succes$(NC)"

# =============================================================================
# URLs
# =============================================================================

urls: ## Affiche toutes les URLs de l'application fil rouge
	@echo "$(GREEN)Reskilling SRE - URLs$(NC)"
	@echo ""
	@echo "  $(YELLOW)Applications$(NC)"
	@echo "    Boutique CapShop:   http://localhost:8080"
	@echo "    Operations Console: http://localhost:8090"
	@echo ""
	@echo "  $(YELLOW)Observabilite$(NC)"
	@echo "    Grafana:            http://localhost:3000  (admin / GRAFANA_ADMIN_PASSWORD dans .env)"
	@echo "    Prometheus:         http://localhost:9090"
	@echo "    Alertmanager:       http://localhost:9093"
	@echo "    Loki et Tempo:      internes au reseau Docker (via Grafana)"
	@echo ""
	@echo "  $(YELLOW)Traffic$(NC)"
	@echo "    Locust:             http://localhost:8089"
