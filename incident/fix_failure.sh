#!/bin/bash

# Script de réparation d'incidents pour le lab SRE
# Fournit des commandes pour réparer les différents types d'incidents

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

# Affiche le menu de réparation
show_menu() {
    echo ""
    echo "RÉPARATEUR D'INCIDENTS SRE LAB"
    echo "================================="
    echo ""
    echo "Choisissez le type de réparation :"
    echo ""
    echo "1.  Restaurer les pods (scale normal)"
    echo "2.  Restaurer les resources (latence normale)"
    echo "3.  Supprimer l'injection d'erreurs"
    echo "4.  Restaurer la connectivité réseau"
    echo "5.  Nettoyer la saturation mémoire"
    echo "6.  Nettoyer la saturation CPU"
    echo "7.  Restaurer les probes de santé"
    echo "8.  Nettoyer les métriques corrompues"
    echo "9.  Restaurer le DNS"
    echo "10. Nettoyage complet"
    echo "11. Diagnostic du système"
    echo "12. Quitter"
    echo ""
}

# Réparation 1: Restaurer les pods
restore_pods() {
    log_info "💀 Restauration des pods..."
    
    if [ -f "/tmp/deployment-backup.yaml" ]; then
        log_info "Restauration depuis la sauvegarde..."
        kubectl apply -f /tmp/deployment-backup.yaml
        log_success "Configuration restaurée depuis la sauvegarde"
    else
        log_info "Sauvegarde non trouvée, restauration manuelle..."
        kubectl scale deployment $DEPLOYMENT_NAME --replicas=3
        log_success "Pods remis à l'échelle normale (3 replicas)"
    fi
    
    echo ""
    log_info "[INFO] Vérification du statut :"
    kubectl get pods -l app=$SERVICE_NAME
}

# Réparation 2: Restaurer les resources
restore_resources() {
    log_info "🐌 Restauration des resources..."
    
    # Restaure les resource limits normales
    kubectl patch deployment $DEPLOYMENT_NAME -p '{
        "spec": {
            "template": {
                "spec": {
                    "containers": [{
                        "name": "url-shortener",
                        "resources": {
                            "limits": {
                                "cpu": "200m",
                                "memory": "256Mi"
                            },
                            "requests": {
                                "cpu": "100m",
                                "memory": "128Mi"
                            }
                        }
                    }]
                }
            }
        }
    }'
    
    log_success "Resource limits restaurées"
    
    echo ""
    log_info "[INFO] Vérification des resources :"
    kubectl describe deployment $DEPLOYMENT_NAME | grep -A 10 "Limits:"
}

# Réparation 3: Supprimer l'injection d'erreurs
remove_error_injection() {
    log_info "💥 Suppression de l'injection d'erreurs..."
    
    # Supprime le ConfigMap d'erreur
    kubectl delete configmap error-injection --ignore-not-found=true
    
    # Restaure la configuration sans les variables d'erreur
    kubectl patch deployment $DEPLOYMENT_NAME -p '{
        "spec": {
            "template": {
                "spec": {
                    "containers": [{
                        "name": "url-shortener",
                        "env": []
                    }]
                }
            }
        }
    }'
    
    log_success "Injection d'erreurs supprimée"
}

# Réparation 4: Restaurer la connectivité réseau
restore_network() {
    log_info "🔌 Restauration de la connectivité réseau..."
    
    # Supprime la NetworkPolicy qui bloque le trafic
    kubectl delete networkpolicy block-all-traffic --ignore-not-found=true
    
    log_success "Connectivité réseau restaurée"
    
    echo ""
    log_info "[INFO] Vérification des NetworkPolicies :"
    kubectl get networkpolicies
}

# Réparation 5: Nettoyer la saturation mémoire
clean_memory_saturation() {
    log_info "💾 Nettoyage de la saturation mémoire..."
    
    # Supprime le pod qui consomme la mémoire
    kubectl delete pod memory-hog --ignore-not-found=true
    
    log_success "Pod de consommation mémoire supprimé"
    
    echo ""
    log_info "[INFO] Vérification des pods :"
    kubectl get pods | grep -v "url-shortener"
}

# Réparation 6: Nettoyer la saturation CPU
clean_cpu_saturation() {
    log_info "[INFO] Nettoyage de la saturation CPU..."
    
    # Supprime le pod qui consomme le CPU
    kubectl delete pod cpu-hog --ignore-not-found=true
    
    log_success "Pod de consommation CPU supprimé"
    
    echo ""
    log_info "[INFO] Vérification des pods :"
    kubectl get pods | grep -v "url-shortener"
}

# Réparation 7: Restaurer les probes de santé
restore_health_probes() {
    log_info "🔄 Restauration des probes de santé..."
    
    # Restaure les probes de santé normaux
    kubectl patch deployment $DEPLOYMENT_NAME -p '{
        "spec": {
            "template": {
                "spec": {
                    "containers": [{
                        "name": "url-shortener",
                        "livenessProbe": {
                            "httpGet": {
                                "path": "/health",
                                "port": 8080
                            },
                            "initialDelaySeconds": 30,
                            "periodSeconds": 10
                        },
                        "readinessProbe": {
                            "httpGet": {
                                "path": "/health",
                                "port": 8080
                            },
                            "initialDelaySeconds": 5,
                            "periodSeconds": 5
                        }
                    }]
                }
            }
        }
    }'
    
    log_success "Probes de santé restaurés"
}

# Réparation 8: Nettoyer les métriques corrompues
clean_corrupted_metrics() {
    log_info "📊 Nettoyage des métriques corrompues..."
    
    # Supprime le pod qui corrompt les métriques
    kubectl delete pod metrics-corrupter --ignore-not-found=true
    
    log_success "Pod de corruption des métriques supprimé"
    
    echo ""
    log_info "[INFO] Vérification des pods :"
    kubectl get pods | grep -v "url-shortener"
}

# Réparation 9: Restaurer le DNS
restore_dns() {
    log_info "🌐 Restauration du DNS..."
    
    # Supprime et recrée le service pour restaurer l'IP
    kubectl delete service $SERVICE_NAME-service
    kubectl apply -f ../kind/manifests/url-shortener-deployment.yaml
    
    log_success "Service DNS restauré"
    
    echo ""
    log_info "[INFO] Vérification du service :"
    kubectl get service $SERVICE_NAME-service
}

# Réparation 10: Nettoyage complet
full_cleanup() {
    log_info "🧹 Nettoyage complet du système..."
    
    # Supprime tous les pods problématiques
    kubectl delete pod memory-hog cpu-hog metrics-corrupter --ignore-not-found=true
    
    # Supprime les ConfigMaps problématiques
    kubectl delete configmap error-injection --ignore-not-found=true
    
    # Supprime les NetworkPolicies problématiques
    kubectl delete networkpolicy block-all-traffic --ignore-not-found=true
    
    # Redémarre le déploiement
    kubectl rollout restart deployment $DEPLOYMENT_NAME
    
    # Attend que le déploiement soit prêt
    kubectl rollout status deployment $DEPLOYMENT_NAME
    
    log_success "Nettoyage complet terminé"
    
    echo ""
    log_info "[INFO] Statut final du système :"
    show_diagnostic
}

# Diagnostic du système
show_diagnostic() {
    log_info "[INFO] Diagnostic du système :"
    echo ""
    
    echo "[INFO] Pods :"
    kubectl get pods -l app=$SERVICE_NAME
    echo ""
    
    echo "[INFO] Services :"
    kubectl get services $SERVICE_NAME-service
    echo ""
    
    echo "[INFO] Déploiements :"
    kubectl get deployments $DEPLOYMENT_NAME
    echo ""
    
    echo "[INFO] Événements récents :"
    kubectl get events --sort-by=.metadata.creationTimestamp | tail -10
    echo ""
    
    echo "[INFO] Logs des pods (dernières 10 lignes) :"
    kubectl logs -l app=$SERVICE_NAME --tail=10
    echo ""
    
    echo "[INFO] Test de connectivité :"
    if kubectl get service $SERVICE_NAME-service &> /dev/null; then
        SERVICE_IP=$(kubectl get service $SERVICE_NAME-service -o jsonpath='{.spec.clusterIP}')
        SERVICE_PORT=$(kubectl get service $SERVICE_NAME-service -o jsonpath='{.spec.ports[0].port}')
        log_info "Service accessible sur $SERVICE_IP:$SERVICE_PORT"
    else
        log_warn "Service non trouvé"
    fi
}

# Fonction principale
main() {
    check_kubectl
    
    while true; do
        show_menu
        read -p "Votre choix (1-12): " choice
        
        case $choice in
            1) restore_pods ;;
            2) restore_resources ;;
            3) remove_error_injection ;;
            4) restore_network ;;
            5) clean_memory_saturation ;;
            6) clean_cpu_saturation ;;
            7) restore_health_probes ;;
            8) clean_corrupted_metrics ;;
            9) restore_dns ;;
            10) full_cleanup ;;
            11) show_diagnostic ;;
            12) 
                log_info "Au revoir!"
                exit 0
                ;;
            *)
                log_error "Choix invalide. Veuillez choisir entre 1 et 12."
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
        "pods") restore_pods ;;
        "resources") restore_resources ;;
        "errors") remove_error_injection ;;
        "network") restore_network ;;
        "memory") clean_memory_saturation ;;
        "cpu") clean_cpu_saturation ;;
        "probes") restore_health_probes ;;
        "metrics") clean_corrupted_metrics ;;
        "dns") restore_dns ;;
        "cleanup") full_cleanup ;;
        "diagnostic") show_diagnostic ;;
        *)
            echo "Usage: $0 [pods|resources|errors|network|memory|cpu|probes|metrics|dns|cleanup|diagnostic]"
            echo "Ou exécutez sans argument pour le menu interactif"
            exit 1
            ;;
    esac
fi
