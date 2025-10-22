#!/usr/bin/env python3
"""
Calculateur de burn rate pour le lab SRE
Calcule le burn rate de l'error budget basé sur les SLOs
"""

import json
import requests
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import argparse
import sys
import numpy as np

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BurnRateCalculator:
    """Calculateur de burn rate pour l'error budget"""
    
    def __init__(self, slo_config_path: str, prometheus_url: str = "http://localhost:9090"):
        self.slo_config = self.load_slo_config(slo_config_path)
        self.prometheus_url = prometheus_url.rstrip('/')
        self.session = requests.Session()
        
    def load_slo_config(self, config_path: str) -> Dict:
        """Charge la configuration des SLOs"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la config SLO: {e}")
            sys.exit(1)
    
    def query_prometheus(self, query: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Exécute une requête Prometheus"""
        try:
            params = {
                'query': query,
                'start': int(start_time.timestamp()),
                'end': int(end_time.timestamp()),
                'step': '60'  # 1 minute
            }
            
            response = self.session.get(
                f"{self.prometheus_url}/api/v1/query_range",
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success':
                    return data['data']['result']
                else:
                    logger.error(f"Erreur Prometheus: {data.get('error', 'Unknown error')}")
                    return []
            else:
                logger.error(f"Erreur HTTP: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Erreur lors de la requête Prometheus: {e}")
            return []
    
    def calculate_availability(self, start_time: datetime, end_time: datetime) -> float:
        """Calcule la disponibilité sur une période"""
        sli_config = self.slo_config['slis']['availability']
        query = sli_config['measurement']['query']
        
        results = self.query_prometheus(query, start_time, end_time)
        
        if not results:
            logger.warning("Aucune donnée de disponibilité trouvée")
            return 0.0
        
        # Calcule la moyenne de la disponibilité
        values = []
        for result in results:
            if 'values' in result:
                for value in result['values']:
                    try:
                        values.append(float(value[1]))
                    except (ValueError, IndexError):
                        continue
        
        if not values:
            return 0.0
        
        return np.mean(values)
    
    def calculate_error_budget_consumed(self, start_time: datetime, end_time: datetime) -> float:
        """Calcule l'error budget consommé"""
        availability = self.calculate_availability(start_time, end_time)
        slo_target = self.slo_config['slis']['availability']['slo_target']
        
        # Error budget consommé = (1 - availability) / (1 - slo_target)
        if slo_target >= 1.0:
            return 0.0
        
        error_budget_consumed = (1 - availability) / (1 - slo_target)
        return min(error_budget_consumed, 1.0)  # Cap à 100%
    
    def calculate_burn_rate(self, start_time: datetime, end_time: datetime) -> float:
        """Calcule le burn rate de l'error budget"""
        duration_hours = (end_time - start_time).total_seconds() / 3600
        error_budget_consumed = self.calculate_error_budget_consumed(start_time, end_time)
        
        if duration_hours == 0:
            return 0.0
        
        # Burn rate = error budget consommé / durée en heures
        burn_rate = error_budget_consumed / duration_hours
        return burn_rate
    
    def calculate_time_to_exhaustion(self, burn_rate: float) -> Optional[float]:
        """Calcule le temps jusqu'à l'épuisement de l'error budget"""
        if burn_rate <= 0:
            return None
        
        # Temps restant = (1 - error budget consommé) / burn rate
        error_budget_consumed = self.calculate_error_budget_consumed(
            datetime.now() - timedelta(hours=1),
            datetime.now()
        )
        
        remaining_budget = 1 - error_budget_consumed
        if remaining_budget <= 0:
            return 0.0
        
        time_to_exhaustion = remaining_budget / burn_rate
        return time_to_exhaustion
    
    def get_burn_rate_alerts(self, burn_rate: float, window_minutes: int) -> List[Dict]:
        """Détermine les alertes de burn rate à déclencher"""
        alerts = []
        alert_configs = self.slo_config['alerting']['burn_rate_alerts']
        
        for alert_name, config in alert_configs.items():
            if (burn_rate >= config['burn_rate_threshold'] and 
                window_minutes >= config['window_minutes']):
                alerts.append({
                    'name': alert_name,
                    'severity': config['severity'],
                    'description': config['description'],
                    'burn_rate': burn_rate,
                    'threshold': config['burn_rate_threshold']
                })
        
        return alerts
    
    def calculate_rolling_burn_rates(self, hours_back: int = 24) -> Dict[str, Dict]:
        """Calcule les burn rates sur différentes fenêtres glissantes"""
        now = datetime.now()
        results = {}
        
        windows = [
            (1, "1h"),
            (6, "6h"),
            (24, "24h"),
            (168, "7d")  # 7 jours
        ]
        
        for window_hours, window_name in windows:
            if window_hours > hours_back:
                continue
                
            start_time = now - timedelta(hours=window_hours)
            end_time = now
            
            burn_rate = self.calculate_burn_rate(start_time, end_time)
            error_budget_consumed = self.calculate_error_budget_consumed(start_time, end_time)
            time_to_exhaustion = self.calculate_time_to_exhaustion(burn_rate)
            alerts = self.get_burn_rate_alerts(burn_rate, window_hours * 60)
            
            results[window_name] = {
                'window_hours': window_hours,
                'burn_rate': burn_rate,
                'error_budget_consumed': error_budget_consumed,
                'time_to_exhaustion_hours': time_to_exhaustion,
                'alerts': alerts
            }
        
        return results
    
    def print_burn_rate_report(self, hours_back: int = 24):
        """Affiche un rapport complet du burn rate"""
        logger.info("[INFO] Calcul du burn rate de l'error budget...")
        
        results = self.calculate_rolling_burn_rates(hours_back)
        
        print("\n" + "="*80)
        print("[INFO] RAPPORT DE BURN RATE - ERROR BUDGET")
        print("="*80)
        print(f"Service: {self.slo_config['service']}")
        print(f"SLO Target: {self.slo_config['slis']['availability']['slo_target_percentage']}%")
        print(f"Error Budget: {self.slo_config['error_budget_policy']['budget_percentage']*100}%")
        print(f"Période d'analyse: {hours_back} heures")
        print()
        
        for window_name, data in results.items():
            print(f"🕐 FENÊTRE {window_name.upper()}")
            print("-" * 40)
            print(f"Burn Rate: {data['burn_rate']:.2f}x")
            print(f"Error Budget Consommé: {data['error_budget_consumed']*100:.2f}%")
            
            if data['time_to_exhaustion_hours'] is not None:
                if data['time_to_exhaustion_hours'] == 0:
                    print("[WARNING] Error budget épuisé!")
                else:
                    print(f"⏰ Temps jusqu'à épuisement: {data['time_to_exhaustion_hours']:.1f} heures")
            else:
                print("[OK] Error budget stable")
            
            # Affiche les alertes
            if data['alerts']:
                print("🚨 ALERTES:")
                for alert in data['alerts']:
                    severity_icon = "🔴" if alert['severity'] == 'critical' else "🟡"
                    print(f"  {severity_icon} {alert['severity'].upper()}: {alert['description']}")
                    print(f"     Burn rate actuel: {alert['burn_rate']:.2f}x (seuil: {alert['threshold']}x)")
            else:
                print("[OK] Aucune alerte")
            
            print()
        
        # Recommandations
        print("[INFO] RECOMMANDATIONS")
        print("-" * 40)
        self.print_recommendations(results)
        print("="*80)
    
    def print_recommendations(self, results: Dict):
        """Affiche des recommandations basées sur le burn rate"""
        max_burn_rate = max(data['burn_rate'] for data in results.values())
        max_alerts = max(len(data['alerts']) for data in results.values())
        
        if max_burn_rate >= 6.0:
            print("🚨 URGENT: Burn rate critique détecté!")
            print("   - Vérifiez immédiatement les métriques")
            print("   - Considérez un rollback ou une mise à l'échelle d'urgence")
            print("   - Activez le mode dégradé si disponible")
        elif max_burn_rate >= 2.0:
            print("[WARNING] ATTENTION: Burn rate élevé")
            print("   - Surveillez de près les métriques")
            print("   - Préparez un plan de mitigation")
            print("   - Vérifiez les déploiements récents")
        elif max_burn_rate >= 1.0:
            print("[INFO] SURVEILLANCE: Burn rate normal mais à surveiller")
            print("   - Continuez la surveillance normale")
            print("   - Vérifiez les tendances")
        else:
            print("[OK] STABLE: Burn rate dans les limites normales")
            print("   - Error budget en bonne santé")
            print("   - Surveillance de routine suffisante")
        
        if max_alerts > 0:
            print(f"\n🔔 {max_alerts} alerte(s) active(s) - Vérifiez les seuils")

def main():
    parser = argparse.ArgumentParser(description='Calculateur de burn rate SRE')
    parser.add_argument('--config', default='slo_config.json',
                       help='Fichier de configuration SLO (défaut: slo_config.json)')
    parser.add_argument('--prometheus', default='http://localhost:9090',
                       help='URL de Prometheus (défaut: http://localhost:9090)')
    parser.add_argument('--hours', type=int, default=24,
                       help='Heures à analyser (défaut: 24)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Mode verbeux')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        calculator = BurnRateCalculator(args.config, args.prometheus)
        calculator.print_burn_rate_report(args.hours)
    except KeyboardInterrupt:
        logger.info("\n[STOP] Calcul interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        logger.error(f"[ERROR] Erreur lors du calcul: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
