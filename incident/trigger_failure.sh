#!/bin/bash

# Script de déclenchement d'incidents pour le lab SRE
# Simule différents types de pannes pour tester les procédures SRE

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

# Vérifie que le cluster est accessible
check_cluster() {
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Impossible de se connecter au cluster Kubernetes"
        exit 1
    fi
    log_success "Cluster Kubernetes accessible"
}

# Affiche le menu des incidents
show_menu() {
    echo ""
    echo "SIMULATEUR D'INCIDENTS SRE LAB"
    echo "================================="
    echo ""
    echo "Choisissez le type d'incident à simuler :"
    echo ""
    echo "1.  Crash de pods (scale à 0)"
    echo "2.  Latence extrême (resource limits)"
    echo "3.  Erreurs 5xx (injection d'erreurs)"
    echo "4.  Perte de connectivité réseau"
    echo "5.  Saturation mémoire"
    echo "6.  Saturation CPU"
    echo "7.  Redémarrage en boucle"
    echo "8.  Métriques corrompues"
    echo "9.  DNS failure"
    echo "10. Mode Chaos (incident aléatoire)"
    echo "11. Statut actuel du système"
    echo "12. Quitter"
    echo ""
}

# Incident 1: Crash de pods
crash_pods() {
    log_info "💀 Simulation d'un crash de pods..."
    
    # Sauvegarde la configuration actuelle
    kubectl get deployment $DEPLOYMENT_NAME -o yaml > /tmp/deployment-backup.yaml
    log_info "Configuration sauvegardée dans /tmp/deployment-backup.yaml"
    
    # Scale à 0
    kubectl scale deployment $DEPLOYMENT_NAME --replicas=0
    log_warn "Pods mis à l'échelle à 0 - Service indisponible!"
    
    echo ""
    log_info "[INFO] Vérification du statut :"
    kubectl get pods -l app=$SERVICE_NAME
    kubectl get services $SERVICE_NAME-service
    
    echo ""
    log_warn "[ALERT] INCIDENT ACTIF - Le service est indisponible!"
    log_info "Utilisez 'kubectl get events --sort-by=.metadata.creationTimestamp' pour voir les événements"
}

# Incident 2: Latence extrême
extreme_latency() {
    log_info "🐌 Simulation d'une latence extrême..."
    
    # Applique des resource limits très restrictives
    kubectl patch deployment $DEPLOYMENT_NAME -p '{
        "spec": {
            "template": {
                "spec": {
                    "containers": [{
                        "name": "url-shortener",
                        "resources": {
                            "limits": {
                                "cpu": "1m",
                                "memory": "1Mi"
                            },
                            "requests": {
                                "cpu": "1m",
                                "memory": "1Mi"
                            }
                        }
                    }]
                }
            }
        }
    }'
    
    log_warn "Resource limits extrêmement restrictives appliquées!"
    log_info "Le service va être très lent..."
    
    echo ""
    log_info "[INFO] Vérification des resources :"
    kubectl describe deployment $DEPLOYMENT_NAME | grep -A 10 "Limits:"
}

# Incident 3: Erreurs 5xx
inject_errors() {
    log_info "💥 Injection d'erreurs 5xx..."
    
    # Crée un ConfigMap avec une configuration d'erreur
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: error-injection
data:
  error-rate: "0.8"
  error-type: "500"
  error-message: "Internal Server Error - Simulated"
EOF
    
    # Monte le ConfigMap dans le pod
    kubectl patch deployment $DEPLOYMENT_NAME -p '{
        "spec": {
            "template": {
                "spec": {
                    "containers": [{
                        "name": "url-shortener",
                        "env": [
                            {"name": "ERROR_RATE", "valueFrom": {"configMapKeyRef": {"name": "error-injection", "key": "error-rate"}}},
                            {"name": "ERROR_TYPE", "valueFrom": {"configMapKeyRef": {"name": "error-injection", "key": "error-type"}}},
                            {"name": "ERROR_MESSAGE", "valueFrom": {"configMapKeyRef": {"name": "error-injection", "key": "error-message"}}}
                        ]
                    }]
                }
            }
        }
    }'
    
    log_warn "80% des requêtes vont maintenant retourner des erreurs 500!"
}

# Incident 4: Perte de connectivité réseau
network_failure() {
    log_info "🔌 Simulation d'une perte de connectivité réseau..."
    
    # Crée un NetworkPolicy qui bloque tout le trafic
    cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: block-all-traffic
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
EOF
    
    log_warn "Tout le trafic réseau est bloqué!"
    log_info "Les pods ne peuvent plus communiquer"
}

# Incident 5: Saturation mémoire
memory_saturation() {
    log_info "💾 Simulation d'une saturation mémoire..."
    
    # Crée un pod qui consomme beaucoup de mémoire
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: memory-hog
spec:
  containers:
  - name: memory-hog
    image: busybox
    command: ["sh", "-c"]
    args: ["while true; do dd if=/dev/zero of=/tmp/memory bs=1M count=1000; sleep 1; done"]
    resources:
      requests:
        memory: "2Gi"
      limits:
        memory: "4Gi"
EOF
    
    log_warn "Pod de consommation mémoire créé!"
    log_info "Cela peut affecter les performances du cluster"
}

# Incident 6: Saturation CPU
cpu_saturation() {
    log_info "[INFO] Simulation d'une saturation CPU..."
    
    # Crée un pod qui consomme beaucoup de CPU
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: cpu-hog
spec:
  containers:
  - name: cpu-hog
    image: busybox
    command: ["sh", "-c"]
    args: ["while true; do :; done"]
    resources:
      requests:
        cpu: "2"
      limits:
        cpu: "4"
EOF
    
    log_warn "Pod de consommation CPU créé!"
    log_info "Cela peut ralentir le cluster"
}

# Incident 7: Redémarrage en boucle
restart_loop() {
    log_info "🔄 Simulation d'un redémarrage en boucle..."
    
    # Applique une configuration qui va causer des redémarrages
    kubectl patch deployment $DEPLOYMENT_NAME -p '{
        "spec": {
            "template": {
                "spec": {
                    "containers": [{
                        "name": "url-shortener",
                        "livenessProbe": {
                            "httpGet": {
                                "path": "/nonexistent",
                                "port": 8080
                            },
                            "initialDelaySeconds": 1,
                            "periodSeconds": 1,
                            "failureThreshold": 1
                        }
                    }]
                }
            }
        }
    }'
    
    log_warn "Les pods vont redémarrer en boucle à cause du probe défaillant!"
}

# Incident 8: Métriques corrompues
corrupt_metrics() {
    log_info "📊 Simulation de métriques corrompues..."
    
    # Crée un pod qui envoie des métriques incorrectes
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: metrics-corrupter
spec:
  containers:
  - name: metrics-corrupter
    image: busybox
    command: ["sh", "-c"]
    args: ["while true; do curl -X POST http://url-shortener-service:80/metrics -d 'corrupted_metric_data'; sleep 1; done"]
EOF
    
    log_warn "Pod de corruption des métriques créé!"
}

# Incident 9: DNS failure
dns_failure() {
    log_info "🌐 Simulation d'un échec DNS..."
    
    # Modifie le DNS du service
    kubectl patch service $SERVICE_NAME-service -p '{
        "spec": {
            "clusterIP": "1.2.3.4"
        }
    }'
    
    log_warn "Adresse IP du service modifiée - DNS failure simulé!"
}

# Incident 10: Mode Chaos
chaos_mode() {
    log_info "[INFO] Mode Chaos - Sélection d'un incident aléatoire..."
    
    incidents=("crash_pods" "extreme_latency" "inject_errors" "network_failure" "memory_saturation")
    selected_incident=${incidents[$RANDOM % ${#incidents[@]}]}
    
    log_info "Incident sélectionné: $selected_incident"
    $selected_incident
}

# Affiche le statut du système
show_status() {
    log_info "[INFO] Statut actuel du système :"
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
    kubectl get events --sort-by=.metadata.creationTimestamp --field-selector type!=Normal | tail -10
}

# Fonction principale
main() {
    check_kubectl
    check_cluster
    
    while true; do
        show_menu
        read -p "Votre choix (1-12): " choice
        
        case $choice in
            1) crash_pods ;;
            2) extreme_latency ;;
            3) inject_errors ;;
            4) network_failure ;;
            5) memory_saturation ;;
            6) cpu_saturation ;;
            7) restart_loop ;;
            8) corrupt_metrics ;;
            9) dns_failure ;;
            10) chaos_mode ;;
            11) show_status ;;
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
        "crash") crash_pods ;;
        "latency") extreme_latency ;;
        "errors") inject_errors ;;
        "network") network_failure ;;
        "memory") memory_saturation ;;
        "cpu") cpu_saturation ;;
        "restart") restart_loop ;;
        "metrics") corrupt_metrics ;;
        "dns") dns_failure ;;
        "chaos") chaos_mode ;;
        "status") show_status ;;
        *)
            echo "Usage: $0 [crash|latency|errors|network|memory|cpu|restart|metrics|dns|chaos|status]"
            echo "Ou exécutez sans argument pour le menu interactif"
            exit 1
            ;;
    esac
fi
