#!/usr/bin/env python3
"""
Suivi de l'error budget pour le lab SRE
Surveille et alerte sur la consommation de l'error budget
"""

import json
import requests
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import argparse
import sys
import sqlite3
import threading
import schedule

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ErrorBudgetTracker:
    """Suivi et surveillance de l'error budget"""
    
    def __init__(self, slo_config_path: str, prometheus_url: str = "http://localhost:9090", 
                 db_path: str = "error_budget.db"):
        self.slo_config = self.load_slo_config(slo_config_path)
        self.prometheus_url = prometheus_url.rstrip('/')
        self.db_path = db_path
        self.session = requests.Session()
        
        # Initialise la base de données
        self.init_database()
        
        # Configuration des alertes
        self.alert_webhook_url = None
        self.alert_email = None
        
    def load_slo_config(self, config_path: str) -> Dict:
        """Charge la configuration des SLOs"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la config SLO: {e}")
            sys.exit(1)
    
    def init_database(self):
        """Initialise la base de données SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table pour stocker les métriques d'error budget
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_budget_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                window_hours INTEGER,
                burn_rate REAL,
                error_budget_consumed REAL,
                availability REAL,
                time_to_exhaustion_hours REAL,
                alerts TEXT
            )
        ''')
        
        # Table pour stocker les alertes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                alert_type TEXT,
                severity TEXT,
                message TEXT,
                burn_rate REAL,
                threshold REAL,
                resolved BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Base de données initialisée")
    
    def query_prometheus(self, query: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Exécute une requête Prometheus"""
        try:
            params = {
                'query': query,
                'start': int(start_time.timestamp()),
                'end': int(end_time.timestamp()),
                'step': '60'
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
        
        return sum(values) / len(values)
    
    def calculate_error_budget_consumed(self, start_time: datetime, end_time: datetime) -> float:
        """Calcule l'error budget consommé"""
        availability = self.calculate_availability(start_time, end_time)
        slo_target = self.slo_config['slis']['availability']['slo_target']
        
        if slo_target >= 1.0:
            return 0.0
        
        error_budget_consumed = (1 - availability) / (1 - slo_target)
        return min(error_budget_consumed, 1.0)
    
    def calculate_burn_rate(self, start_time: datetime, end_time: datetime) -> float:
        """Calcule le burn rate de l'error budget"""
        duration_hours = (end_time - start_time).total_seconds() / 3600
        error_budget_consumed = self.calculate_error_budget_consumed(start_time, end_time)
        
        if duration_hours == 0:
            return 0.0
        
        return error_budget_consumed / duration_hours
    
    def calculate_time_to_exhaustion(self, burn_rate: float) -> Optional[float]:
        """Calcule le temps jusqu'à l'épuisement de l'error budget"""
        if burn_rate <= 0:
            return None
        
        now = datetime.now()
        error_budget_consumed = self.calculate_error_budget_consumed(
            now - timedelta(hours=1),
            now
        )
        
        remaining_budget = 1 - error_budget_consumed
        if remaining_budget <= 0:
            return 0.0
        
        return remaining_budget / burn_rate
    
    def check_alerts(self, burn_rate: float, window_hours: int) -> List[Dict]:
        """Vérifie les alertes de burn rate"""
        alerts = []
        alert_configs = self.slo_config['alerting']['burn_rate_alerts']
        
        for alert_name, config in alert_configs.items():
            if (burn_rate >= config['burn_rate_threshold'] and 
                window_hours * 60 >= config['window_minutes']):
                
                alert = {
                    'type': alert_name,
                    'severity': config['severity'],
                    'message': config['description'],
                    'burn_rate': burn_rate,
                    'threshold': config['burn_rate_threshold'],
                    'window_hours': window_hours
                }
                alerts.append(alert)
        
        return alerts
    
    def store_metrics(self, window_hours: int, burn_rate: float, 
                     error_budget_consumed: float, availability: float,
                     time_to_exhaustion: Optional[float], alerts: List[Dict]):
        """Stocke les métriques dans la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO error_budget_metrics 
            (window_hours, burn_rate, error_budget_consumed, availability, 
             time_to_exhaustion_hours, alerts)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            window_hours,
            burn_rate,
            error_budget_consumed,
            availability,
            time_to_exhaustion,
            json.dumps(alerts)
        ))
        
        # Stocke les alertes
        for alert in alerts:
            cursor.execute('''
                INSERT INTO alerts (alert_type, severity, message, burn_rate, threshold)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                alert['type'],
                alert['severity'],
                alert['message'],
                alert['burn_rate'],
                alert['threshold']
            ))
        
        conn.commit()
        conn.close()
    
    def send_alert(self, alert: Dict):
        """Envoie une alerte (webhook, email, etc.)"""
        logger.warning(f"🚨 ALERTE {alert['severity'].upper()}: {alert['message']}")
        logger.warning(f"   Burn rate: {alert['burn_rate']:.2f}x (seuil: {alert['threshold']}x)")
        
        # Ici, vous pourriez ajouter l'envoi d'emails, webhooks, etc.
        if self.alert_webhook_url:
            self.send_webhook_alert(alert)
        
        if self.alert_email:
            self.send_email_alert(alert)
    
    def send_webhook_alert(self, alert: Dict):
        """Envoie une alerte via webhook"""
        try:
            payload = {
                'text': f"🚨 {alert['severity'].upper()}: {alert['message']}",
                'attachments': [{
                    'color': 'danger' if alert['severity'] == 'critical' else 'warning',
                    'fields': [
                        {'title': 'Burn Rate', 'value': f"{alert['burn_rate']:.2f}x", 'short': True},
                        {'title': 'Seuil', 'value': f"{alert['threshold']}x", 'short': True},
                        {'title': 'Service', 'value': self.slo_config['service'], 'short': True},
                        {'title': 'Timestamp', 'value': datetime.now().isoformat(), 'short': True}
                    ]
                }]
            }
            
            response = self.session.post(self.alert_webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("Alerte webhook envoyée")
            else:
                logger.error(f"Erreur envoi webhook: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Erreur envoi webhook: {e}")
    
    def send_email_alert(self, alert: Dict):
        """Envoie une alerte par email (placeholder)"""
        # Ici, vous pourriez implémenter l'envoi d'emails
        logger.info(f"Email alerte à {self.alert_email}: {alert['message']}")
    
    def collect_metrics(self):
        """Collecte les métriques d'error budget"""
        logger.info("📊 Collecte des métriques d'error budget...")
        
        now = datetime.now()
        windows = [1, 6, 24]  # 1h, 6h, 24h
        
        for window_hours in windows:
            start_time = now - timedelta(hours=window_hours)
            
            # Calcule les métriques
            availability = self.calculate_availability(start_time, now)
            error_budget_consumed = self.calculate_error_budget_consumed(start_time, now)
            burn_rate = self.calculate_burn_rate(start_time, now)
            time_to_exhaustion = self.calculate_time_to_exhaustion(burn_rate)
            
            # Vérifie les alertes
            alerts = self.check_alerts(burn_rate, window_hours)
            
            # Stocke les métriques
            self.store_metrics(
                window_hours, burn_rate, error_budget_consumed, 
                availability, time_to_exhaustion, alerts
            )
            
            # Envoie les alertes
            for alert in alerts:
                self.send_alert(alert)
            
            logger.info(f"Fenêtre {window_hours}h - Burn rate: {burn_rate:.2f}x, "
                       f"Error budget: {error_budget_consumed*100:.2f}%, "
                       f"Alertes: {len(alerts)}")
    
    def get_historical_data(self, hours: int = 24) -> List[Dict]:
        """Récupère les données historiques"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM error_budget_metrics 
            WHERE timestamp > datetime('now', '-{} hours')
            ORDER BY timestamp DESC
        '''.format(hours))
        
        columns = [description[0] for description in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            result = dict(zip(columns, row))
            result['alerts'] = json.loads(result['alerts']) if result['alerts'] else []
            results.append(result)
        
        conn.close()
        return results
    
    def print_dashboard(self):
        """Affiche un tableau de bord de l'error budget"""
        logger.info("📊 Tableau de bord de l'error budget...")
        
        # Collecte les métriques actuelles
        self.collect_metrics()
        
        # Récupère les données historiques
        historical_data = self.get_historical_data(24)
        
        print("\n" + "="*80)
        print("📊 TABLEAU DE BORD ERROR BUDGET")
        print("="*80)
        print(f"Service: {self.slo_config['service']}")
        print(f"SLO Target: {self.slo_config['slis']['availability']['slo_target_percentage']}%")
        print(f"Error Budget: {self.slo_config['error_budget_policy']['budget_percentage']*100}%")
        print(f"Dernière mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Affiche les métriques actuelles
        if historical_data:
            latest = historical_data[0]
            print("📈 MÉTRIQUES ACTUELLES (1h)")
            print("-" * 40)
            print(f"Burn Rate: {latest['burn_rate']:.2f}x")
            print(f"Error Budget Consommé: {latest['error_budget_consumed']*100:.2f}%")
            print(f"Disponibilité: {latest['availability']*100:.2f}%")
            
            if latest['time_to_exhaustion_hours'] is not None:
                if latest['time_to_exhaustion_hours'] == 0:
                    print("[WARNING] Error budget épuisé!")
                else:
                    print(f"⏰ Temps jusqu'à épuisement: {latest['time_to_exhaustion_hours']:.1f}h")
            
            if latest['alerts']:
                print("🚨 ALERTES ACTIVES:")
                for alert in latest['alerts']:
                    severity_icon = "🔴" if alert['severity'] == 'critical' else "🟡"
                    print(f"  {severity_icon} {alert['severity'].upper()}: {alert['message']}")
            else:
                print("[OK] Aucune alerte active")
        
        print()
        
        # Affiche les tendances
        if len(historical_data) > 1:
            print("📊 TENDANCES (24h)")
            print("-" * 40)
            
            # Calcule les tendances
            burn_rates = [d['burn_rate'] for d in historical_data[:6]]  # 6 dernières heures
            if len(burn_rates) >= 2:
                trend = "[UP]" if burn_rates[0] > burn_rates[-1] else "[DOWN]"
                print(f"Tendance burn rate: {trend}")
                print(f"Burn rate moyen: {sum(burn_rates)/len(burn_rates):.2f}x")
        
        print("="*80)
    
    def start_monitoring(self, interval_minutes: int = 5):
        """Démarre la surveillance continue"""
        logger.info(f"🔄 Démarrage de la surveillance (intervalle: {interval_minutes}min)")
        
        # Planifie la collecte des métriques
        schedule.every(interval_minutes).minutes.do(self.collect_metrics)
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Vérifie chaque minute
        except KeyboardInterrupt:
            logger.info("[STOP] Surveillance arrêtée par l'utilisateur")

def main():
    parser = argparse.ArgumentParser(description='Suivi de l\'error budget SRE')
    parser.add_argument('--config', default='slo_config.json',
                       help='Fichier de configuration SLO (défaut: slo_config.json)')
    parser.add_argument('--prometheus', default='http://localhost:9090',
                       help='URL de Prometheus (défaut: http://localhost:9090)')
    parser.add_argument('--db', default='error_budget.db',
                       help='Chemin de la base de données (défaut: error_budget.db)')
    parser.add_argument('--webhook', help='URL du webhook pour les alertes')
    parser.add_argument('--email', help='Email pour les alertes')
    parser.add_argument('--monitor', action='store_true',
                       help='Démarre la surveillance continue')
    parser.add_argument('--interval', type=int, default=5,
                       help='Intervalle de surveillance en minutes (défaut: 5)')
    parser.add_argument('--dashboard', action='store_true',
                       help='Affiche le tableau de bord')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Mode verbeux')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        tracker = ErrorBudgetTracker(args.config, args.prometheus, args.db)
        
        if args.webhook:
            tracker.alert_webhook_url = args.webhook
        if args.email:
            tracker.alert_email = args.email
        
        if args.dashboard:
            tracker.print_dashboard()
        elif args.monitor:
            tracker.start_monitoring(args.interval)
        else:
            # Mode par défaut: collecte unique
            tracker.collect_metrics()
            tracker.print_dashboard()
            
    except KeyboardInterrupt:
        logger.info("\n[STOP] Programme interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        logger.error(f"[ERROR] Erreur: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
