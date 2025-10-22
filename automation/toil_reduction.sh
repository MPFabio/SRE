#!/bin/bash

# Script d'automatisation pour réduire le toil
# Implémente des automatisations basées sur les leçons apprises des incidents

set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="default"
SERVICE_NAME="url-shortener"
DEPLOYMENT_NAME="url-shortener"
MONITORING_INTERVAL=30  # secondes

# Fonctions utilitaires
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Vérifie que kubectl est disponible
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl n'est pas installé ou n'est pas dans le PATH"
        exit 1
    fi
}

# Vérifie la santé du service
check_service_health() {
    local service_url="http://localhost:30000"
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$service_url/health" > /dev/null 2>&1; then
            return 0
        fi
        
        log_warn "Tentative $attempt/$max_attempts échouée pour $service_url"
        sleep 5
        ((attempt++))
    done
    
    return 1
}

# Vérifie les métriques de performance
check_performance_metrics() {
    local service_url="http://localhost:30000"
    
    # Récupère les métriques Prometheus
    local metrics=$(curl -s "$service_url/metrics" 2>/dev/null || echo "")
    
    if [ -z "$metrics" ]; then
        log_warn "Impossible de récupérer les métriques"
        return 1
    fi
    
    # Extrait les métriques importantes
    local http_requests=$(echo "$metrics" | grep "http_requests_total" | tail -1 | awk '{print $2}' || echo "0")
    local error_rate=$(echo "$metrics" | grep "http_requests_total{status=~\"[45]..\"}" | awk '{print $2}' || echo "0")
    local avg_latency=$(echo "$metrics" | grep "http_request_duration_seconds_sum" | awk '{print $2}' || echo "0")
    
    log_info "Métriques actuelles:"
    log_info "  - Requêtes totales: $http_requests"
    log_info "  - Taux d'erreur: $error_rate"
    log_info "  - Latence moyenne: $avg_latency"
    
    return 0
}

# Auto-scaling basé sur les métriques
auto_scale() {
    local current_replicas=$(kubectl get deployment $DEPLOYMENT_NAME -o jsonpath='{.spec.replicas}')
    local max_replicas=10
    local min_replicas=2
    
    # Vérifie la charge CPU (simulée)
    local cpu_usage=$(kubectl top pods -l app=$SERVICE_NAME --no-headers 2>/dev/null | awk '{print $2}' | sed 's/m//' | head -1 || echo "0")
    
    if [ "$cpu_usage" -gt 80 ] && [ "$current_replicas" -lt "$max_replicas" ]; then
        log_warn "Charge CPU élevée ($cpu_usage%), mise à l'échelle vers le haut"
        kubectl scale deployment $DEPLOYMENT_NAME --replicas=$((current_replicas + 1))
        log_success "Mise à l'échelle vers le haut: $current_replicas -> $((current_replicas + 1))"
    elif [ "$cpu_usage" -lt 20 ] && [ "$current_replicas" -gt "$min_replicas" ]; then
        log_info "Charge CPU faible ($cpu_usage%), mise à l'échelle vers le bas"
        kubectl scale deployment $DEPLOYMENT_NAME --replicas=$((current_replicas - 1))
        log_success "Mise à l'échelle vers le bas: $current_replicas -> $((current_replicas - 1))"
    else
        log_info "Charge CPU normale ($cpu_usage%), pas de changement nécessaire"
    fi
}

# Redémarrage automatique des pods défaillants
restart_failed_pods() {
    local failed_pods=$(kubectl get pods -l app=$SERVICE_NAME --field-selector=status.phase=Failed --no-headers | wc -l)
    
    if [ "$failed_pods" -gt 0 ]; then
        log_warn "$failed_pods pod(s) en échec détecté(s), redémarrage automatique"
        
        # Supprime les pods en échec
        kubectl get pods -l app=$SERVICE_NAME --field-selector=status.phase=Failed -o name | xargs -r kubectl delete
        
        # Attend que les nouveaux pods soient prêts
        kubectl wait --for=condition=Ready pods -l app=$SERVICE_NAME --timeout=300s
        
        log_success "Pods défaillants redémarrés"
    else
        log_info "Aucun pod en échec détecté"
    fi
}

# Nettoyage automatique des ressources
cleanup_resources() {
    log_info "🧹 Nettoyage automatique des ressources..."
    
    # Supprime les pods terminés
    local terminated_pods=$(kubectl get pods --field-selector=status.phase=Succeeded --no-headers | wc -l)
    if [ "$terminated_pods" -gt 0 ]; then
        kubectl get pods --field-selector=status.phase=Succeeded -o name | xargs -r kubectl delete
        log_info "Pods terminés supprimés: $terminated_pods"
    fi
    
    # Supprime les pods en échec anciens (> 1 heure)
    local old_failed_pods=$(kubectl get pods --field-selector=status.phase=Failed --no-headers | awk '$4 ~ /[0-9]+h/ {print $1}' | wc -l)
    if [ "$old_failed_pods" -gt 0 ]; then
        kubectl get pods --field-selector=status.phase=Failed --no-headers | awk '$4 ~ /[0-9]+h/ {print $1}' | xargs -r kubectl delete pod
        log_info "Anciens pods en échec supprimés: $old_failed_pods"
    fi
    
    # Nettoie les événements anciens
    kubectl get events --field-selector=type!=Normal --sort-by=.metadata.creationTimestamp | tail -n +50 | awk '{print $1}' | xargs -r kubectl delete events 2>/dev/null || true
    
    log_success "Nettoyage terminé"
}

# Surveillance des seuils d'alerte
monitor_thresholds() {
    local service_url="http://localhost:30000"
    
    # Vérifie la disponibilité
    if ! check_service_health; then
        log_error "Service indisponible - Déclenchement d'alertes"
        send_alert "Service indisponible" "critical"
        return 1
    fi
    
    # Vérifie le taux d'erreur
    local error_rate=$(curl -s "$service_url/metrics" 2>/dev/null | grep "http_requests_total{status=~\"[45]..\"}" | awk '{print $2}' || echo "0")
    if [ "$error_rate" -gt 10 ]; then
        log_warn "Taux d'erreur élevé: $error_rate%"
        send_alert "Taux d'erreur élevé: $error_rate%" "warning"
    fi
    
    # Vérifie la latence
    local avg_latency=$(curl -s "$service_url/metrics" 2>/dev/null | grep "http_request_duration_seconds_sum" | awk '{print $2}' || echo "0")
    if (( $(echo "$avg_latency > 2.0" | bc -l) )); then
        log_warn "Latence élevée: ${avg_latency}s"
        send_alert "Latence élevée: ${avg_latency}s" "warning"
    fi
}

# Envoi d'alertes
send_alert() {
    local message="$1"
    local severity="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    log_warn "🚨 ALERTE $severity: $message"
    
    # Ici, vous pourriez ajouter l'envoi d'emails, webhooks, etc.
    # Pour ce lab, on log simplement l'alerte
    echo "[$timestamp] ALERTE $severity: $message" >> /tmp/sre-alerts.log
}

# Déploiement automatique avec rollback
auto_deploy() {
    local image_tag="$1"
    
    if [ -z "$image_tag" ]; then
        log_error "Tag d'image requis pour le déploiement"
        return 1
    fi
    
    log_info "🚀 Déploiement automatique de l'image: $image_tag"
    
    # Sauvegarde la version actuelle
    kubectl get deployment $DEPLOYMENT_NAME -o yaml > /tmp/deployment-backup-$(date +%s).yaml
    
    # Met à jour l'image
    kubectl set image deployment/$DEPLOYMENT_NAME url-shortener=url-shortener:$image_tag
    
    # Attend que le déploiement soit prêt
    if kubectl rollout status deployment/$DEPLOYMENT_NAME --timeout=300s; then
        log_success "Déploiement réussi"
        
        # Vérifie la santé après déploiement
        sleep 30
        if check_service_health; then
            log_success "Service en bonne santé après déploiement"
        else
            log_error "Service défaillant après déploiement - Rollback automatique"
            auto_rollback
        fi
    else
        log_error "Déploiement échoué - Rollback automatique"
        auto_rollback
    fi
}

# Rollback automatique
auto_rollback() {
    log_warn "🔄 Rollback automatique en cours..."
    
    # Trouve la dernière sauvegarde
    local latest_backup=$(ls -t /tmp/deployment-backup-*.yaml 2>/dev/null | head -1)
    
    if [ -n "$latest_backup" ]; then
        kubectl apply -f "$latest_backup"
        log_success "Rollback effectué depuis $latest_backup"
    else
        log_error "Aucune sauvegarde trouvée pour le rollback"
        # Rollback vers la révision précédente
        kubectl rollout undo deployment/$DEPLOYMENT_NAME
    fi
}

# Surveillance continue
continuous_monitoring() {
    log_info "🔄 Démarrage de la surveillance continue (intervalle: ${MONITORING_INTERVAL}s)"
    
    while true; do
        log_info "=== Surveillance $(date '+%Y-%m-%d %H:%M:%S') ==="
        
        # Vérifie la santé du service
        if check_service_health; then
            log_success "Service en bonne santé"
            
            # Vérifie les métriques de performance
            check_performance_metrics
            
            # Auto-scaling
            auto_scale
            
            # Surveillance des seuils
            monitor_thresholds
        else
            log_error "Service défaillant - Tentative de réparation"
            restart_failed_pods
        fi
        
        # Nettoyage périodique
        cleanup_resources
        
        log_info "Prochaine vérification dans ${MONITORING_INTERVAL} secondes..."
        sleep $MONITORING_INTERVAL
    done
}

# Affiche le menu
show_menu() {
    echo ""
    echo "🤖 AUTOMATISATION SRE - RÉDUCTION DU TOIL"
    echo "=========================================="
    echo ""
    echo "Choisissez une action :"
    echo ""
    echo "1.  🔍 Vérifier la santé du service"
    echo "2.  📊 Afficher les métriques de performance"
    echo "3.  📈 Auto-scaling basé sur les métriques"
    echo "4.  🔄 Redémarrer les pods défaillants"
    echo "5.  🧹 Nettoyer les ressources"
    echo "6.  🚨 Vérifier les seuils d'alerte"
    echo "7.  🚀 Déploiement automatique"
    echo "8.  🔄 Rollback automatique"
    echo "9.  🔄 Surveillance continue"
    echo "10. 📋 Statut du système"
    echo "11. ❌ Quitter"
    echo ""
}

# Affiche le statut du système
show_status() {
    log_info "📋 Statut du système :"
    echo ""
    
    echo "🔍 Pods :"
    kubectl get pods -l app=$SERVICE_NAME
    echo ""
    
    echo "🌐 Services :"
    kubectl get services $SERVICE_NAME-service
    echo ""
    
    echo "📊 Déploiements :"
    kubectl get deployments $DEPLOYMENT_NAME
    echo ""
    
    echo "📈 Métriques :"
    check_performance_metrics
    echo ""
    
    echo "🚨 Alertes récentes :"
    if [ -f "/tmp/sre-alerts.log" ]; then
        tail -5 /tmp/sre-alerts.log
    else
        echo "Aucune alerte récente"
    fi
}

# Fonction principale
main() {
    check_kubectl
    
    while true; do
        show_menu
        read -p "Votre choix (1-11): " choice
        
        case $choice in
            1) check_service_health ;;
            2) check_performance_metrics ;;
            3) auto_scale ;;
            4) restart_failed_pods ;;
            5) cleanup_resources ;;
            6) monitor_thresholds ;;
            7) 
                read -p "Tag d'image: " image_tag
                auto_deploy "$image_tag"
                ;;
            8) auto_rollback ;;
            9) continuous_monitoring ;;
            10) show_status ;;
            11) 
                log_info "Au revoir!"
                exit 0
                ;;
            *)
                log_error "Choix invalide. Veuillez choisir entre 1 et 11."
                ;;
        esac
        
        echo ""
        read -p "Appuyez sur Entrée pour continuer..."
    done
}

# Gestion des arguments en ligne de commande
if [ $# -eq 0 ]; then
    main
else
    case $1 in
        "health") check_service_health ;;
        "metrics") check_performance_metrics ;;
        "scale") auto_scale ;;
        "restart") restart_failed_pods ;;
        "cleanup") cleanup_resources ;;
        "monitor") monitor_thresholds ;;
        "deploy") auto_deploy "$2" ;;
        "rollback") auto_rollback ;;
        "continuous") continuous_monitoring ;;
        "status") show_status ;;
        *)
            echo "Usage: $0 [health|metrics|scale|restart|cleanup|monitor|deploy <tag>|rollback|continuous|status]"
            echo "Ou exécutez sans argument pour le menu interactif"
            exit 1
            ;;
    esac
fi
