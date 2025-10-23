#!/usr/bin/env python3
"""
Script d'ingestion de données vers Splunk
Génère et injecte des logs, métriques et traces simulés
"""

import requests
import json
import time
import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import argparse
import sys
import uuid

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SplunkIngester:
    """Classe pour l'ingestion de données vers Splunk"""
    
    def __init__(self, splunk_url: str, hec_token: str):
        self.splunk_url = splunk_url.rstrip('/')
        self.hec_token = hec_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Splunk {hec_token}',
            'Content-Type': 'application/json'
        })
        
        # Configuration des endpoints
        self.logs_endpoint = f"{self.splunk_url}/services/collector/event"
        self.metrics_endpoint = f"{self.splunk_url}/services/collector/event"
        self.traces_endpoint = f"{self.splunk_url}/services/collector/event"
    
    def test_connection(self) -> bool:
        """Teste la connexion à Splunk"""
        try:
            response = self.session.get(f"{self.splunk_url}/services/server/info")
            if response.status_code == 200:
                logger.info("[OK] Connexion à Splunk réussie")
                return True
            else:
                logger.error(f"[ERROR] Erreur de connexion: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"[ERROR] Impossible de se connecter à Splunk: {e}")
            return False
    
    def generate_log_events(self, count: int, days_back: int = 30) -> List[Dict]:
        """Génère des événements de log simulés"""
        events = []
        base_time = datetime.now() - timedelta(days=days_back)
        
        log_levels = ['INFO', 'WARN', 'ERROR', 'DEBUG']
        services = ['url-shortener', 'database', 'cache', 'auth-service']
        operations = ['shorten_url', 'redirect_url', 'health_check', 'metrics_collection']
        
        for i in range(count):
            # Génère un timestamp aléatoire dans la période
            random_days = random.randint(0, days_back)
            random_hours = random.randint(0, 23)
            random_minutes = random.randint(0, 59)
            random_seconds = random.randint(0, 59)
            
            event_time = base_time + timedelta(
                days=random_days,
                hours=random_hours,
                minutes=random_minutes,
                seconds=random_seconds
            )
            
            # Génère le contenu du log
            level = random.choices(log_levels, weights=[50, 20, 10, 20])[0]
            service = random.choice(services)
            operation = random.choice(operations)
            
            # Messages de log réalistes
            if level == 'INFO':
                messages = [
                    f"Request processed successfully for {operation}",
                    f"URL shortened: {uuid.uuid4().hex[:8]}",
                    f"Health check passed for {service}",
                    f"Cache hit for key: {uuid.uuid4().hex[:12]}"
                ]
            elif level == 'WARN':
                messages = [
                    f"High latency detected for {operation}: {random.randint(1000, 5000)}ms",
                    f"Cache miss for {service}",
                    f"Rate limit approaching for IP: 192.168.1.{random.randint(1, 254)}",
                    f"Memory usage high: {random.randint(70, 90)}%"
                ]
            elif level == 'ERROR':
                messages = [
                    f"Failed to process {operation}: {random.choice(['timeout', 'connection refused', 'invalid input'])}",
                    f"Database connection failed for {service}",
                    f"Authentication failed for user: {uuid.uuid4().hex[:8]}",
                    f"Out of memory error in {service}"
                ]
            else:  # DEBUG
                messages = [
                    f"Processing {operation} with params: {uuid.uuid4().hex[:16]}",
                    f"Cache lookup for {service}",
                    f"Starting transaction for {operation}",
                    f"Validating input for {operation}"
                ]
            
            message = random.choice(messages)
            
            # Génère des métadonnées
            metadata = {
                'service': service,
                'operation': operation,
                'level': level,
                'request_id': str(uuid.uuid4()),
                'user_id': f"user_{random.randint(1000, 9999)}",
                'ip_address': f"192.168.1.{random.randint(1, 254)}",
                'user_agent': random.choice([
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
                ]),
                'response_time_ms': random.randint(10, 2000),
                'status_code': random.choice([200, 201, 400, 404, 500])
            }
            
            event = {
                'time': int(event_time.timestamp()),
                'source': f'sre-lab-{service}',
                'sourcetype': 'sre:logs',
                'index': 'main',
                'event': {
                    'message': message,
                    'timestamp': event_time.isoformat(),
                    'metadata': metadata
                }
            }
            
            events.append(event)
        
        return events
    
    def generate_metric_events(self, count: int, days_back: int = 30) -> List[Dict]:
        """Génère des événements de métriques simulés"""
        events = []
        base_time = datetime.now() - timedelta(days=days_back)
        
        metric_types = [
            'http_requests_total',
            'http_request_duration_seconds',
            'urls_created_total',
            'urls_redirected_total',
            'memory_usage_bytes',
            'cpu_usage_percent',
            'database_connections_active',
            'cache_hit_ratio'
        ]
        
        for i in range(count):
            # Génère un timestamp aléatoire
            random_days = random.randint(0, days_back)
            random_hours = random.randint(0, 23)
            random_minutes = random.randint(0, 59)
            
            event_time = base_time + timedelta(
                days=random_days,
                hours=random_hours,
                minutes=random_minutes
            )
            
            metric_type = random.choice(metric_types)
            
            # Génère des valeurs de métriques réalistes
            if 'total' in metric_type:
                value = random.randint(1, 1000)
            elif 'duration' in metric_type:
                value = round(random.uniform(0.001, 2.0), 3)
            elif 'percent' in metric_type:
                value = round(random.uniform(0, 100), 2)
            elif 'ratio' in metric_type:
                value = round(random.uniform(0, 1), 3)
            else:
                value = random.randint(1000, 1000000)
            
            # Labels pour les métriques
            labels = {
                'service': 'url-shortener',
                'instance': f'pod-{random.randint(1, 3)}',
                'method': random.choice(['GET', 'POST']),
                'endpoint': random.choice(['/shorten', '/{short_code}', '/health', '/metrics']),
                'status_code': str(random.choice([200, 201, 400, 404, 500]))
            }
            
            event = {
                'time': int(event_time.timestamp()),
                'source': 'sre-lab-metrics',
                'sourcetype': 'sre:metrics',
                'index': 'main',
                'event': {
                    'metric_name': metric_type,
                    'value': value,
                    'labels': labels,
                    'timestamp': event_time.isoformat()
                }
            }
            
            events.append(event)
        
        return events
    
    def generate_trace_events(self, count: int, days_back: int = 30) -> List[Dict]:
        """Génère des événements de traces simulés"""
        events = []
        base_time = datetime.now() - timedelta(days=days_back)
        
        operations = [
            'shorten_url',
            'redirect_url',
            'database_query',
            'cache_lookup',
            'external_api_call'
        ]
        
        for i in range(count):
            # Génère un timestamp aléatoire
            random_days = random.randint(0, days_back)
            random_hours = random.randint(0, 23)
            random_minutes = random.randint(0, 59)
            random_seconds = random.randint(0, 59)
            
            event_time = base_time + timedelta(
                days=random_days,
                hours=random_hours,
                minutes=random_minutes,
                seconds=random_seconds
            )
            
            operation = random.choice(operations)
            trace_id = str(uuid.uuid4())
            span_id = str(uuid.uuid4())
            parent_span_id = str(uuid.uuid4()) if random.random() > 0.3 else None
            
            # Durée de la span
            duration_ms = random.randint(1, 2000)
            
            # Génère des attributs de span
            attributes = {
                'service.name': 'url-shortener',
                'service.version': '1.0.0',
                'operation.name': operation,
                'http.method': random.choice(['GET', 'POST']),
                'http.url': f'http://localhost:30000/{operation}',
                'http.status_code': random.choice([200, 201, 400, 404, 500]),
                'user.id': f'user_{random.randint(1000, 9999)}',
                'request.id': str(uuid.uuid4()),
                'span.kind': 'server'
            }
            
            # Génère des événements de span
            span_events = []
            if random.random() > 0.7:  # 30% des spans ont des événements
                event_count = random.randint(1, 3)
                for _ in range(event_count):
                    span_events.append({
                        'name': random.choice(['cache_hit', 'cache_miss', 'database_query', 'external_call']),
                        'timestamp': event_time.isoformat(),
                        'attributes': {
                            'event.type': 'log',
                            'event.message': f'Event in {operation}'
                        }
                    })
            
            event = {
                'time': int(event_time.timestamp()),
                'source': 'sre-lab-traces',
                'sourcetype': 'sre:traces',
                'index': 'main',
                'event': {
                    'trace_id': trace_id,
                    'span_id': span_id,
                    'parent_span_id': parent_span_id,
                    'operation_name': operation,
                    'start_time': event_time.isoformat(),
                    'duration_ms': duration_ms,
                    'attributes': attributes,
                    'events': span_events,
                    'status': random.choice(['OK', 'ERROR']),
                    'timestamp': event_time.isoformat()
                }
            }
            
            events.append(event)
        
        return events
    
    def send_events(self, events: List[Dict], event_type: str) -> bool:
        """Envoie les événements vers Splunk"""
        if not events:
            return True
        
        # Divise en batches pour éviter les timeouts
        batch_size = 100
        total_batches = (len(events) + batch_size - 1) // batch_size
        
        logger.info(f"📤 Envoi de {len(events)} événements {event_type} en {total_batches} batches...")
        
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            
            try:
                response = self.session.post(
                    self.logs_endpoint,
                    data=json.dumps(batch),
                    timeout=30
                )
                
                if response.status_code == 200:
                    logger.debug(f"[OK] Batch {i//batch_size + 1}/{total_batches} envoyé")
                else:
                    logger.error(f"[ERROR] Erreur batch {i//batch_size + 1}: {response.status_code} - {response.text}")
                    return False
                    
            except Exception as e:
                logger.error(f"[ERROR] Erreur lors de l'envoi du batch {i//batch_size + 1}: {e}")
                return False
            
            # Pause entre les batches
            time.sleep(0.1)
        
        logger.info(f"[OK] Tous les événements {event_type} ont été envoyés")
        return True
    
    def ingest_all_data(self, log_count: int = 10000, metric_count: int = 5000, 
                       trace_count: int = 3000, days_back: int = 30):
        """Ingère tous les types de données"""
        logger.info("[START] Démarrage de l'ingestion de données vers Splunk")
        
        # Test de connexion
        if not self.test_connection():
            return False
        
        # Génère et envoie les logs
        logger.info("📝 Génération des logs...")
        log_events = self.generate_log_events(log_count, days_back)
        if not self.send_events(log_events, "logs"):
            return False
        
        # Génère et envoie les métriques
        logger.info("[INFO] Génération des métriques...")
        metric_events = self.generate_metric_events(metric_count, days_back)
        if not self.send_events(metric_events, "métriques"):
            return False
        
        # Génère et envoie les traces
        logger.info("[INFO] Génération des traces...")
        trace_events = self.generate_trace_events(trace_count, days_back)
        if not self.send_events(trace_events, "traces"):
            return False
        
        logger.info("[SUCCESS] Ingestion terminée avec succès!")
        return True

def main():
    parser = argparse.ArgumentParser(description='Ingestion de données vers Splunk')
    parser.add_argument('--splunk-url', default='http://localhost:8000',
                       help='URL de Splunk (défaut: http://localhost:8000)')
    parser.add_argument('--hec-token', default=os.getenv('SPLUNK_HEC_TOKEN', 'your-hec-token-here'),
                       help='Token HEC Splunk (défaut: variable d\'environnement SPLUNK_HEC_TOKEN)')
    parser.add_argument('--logs', type=int, default=10000,
                       help='Nombre d\'événements de logs (défaut: 10000)')
    parser.add_argument('--metrics', type=int, default=5000,
                       help='Nombre d\'événements de métriques (défaut: 5000)')
    parser.add_argument('--traces', type=int, default=3000,
                       help='Nombre d\'événements de traces (défaut: 3000)')
    parser.add_argument('--days', type=int, default=30,
                       help='Nombre de jours en arrière (défaut: 30)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Mode verbeux')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    ingester = SplunkIngester(args.splunk_url, args.hec_token)
    
    try:
        success = ingester.ingest_all_data(
            log_count=args.logs,
            metric_count=args.metrics,
            trace_count=args.traces,
            days_back=args.days
        )
        
        if success:
            logger.info("[OK] Ingestion terminée avec succès!")
            sys.exit(0)
        else:
            logger.error("[ERROR] Échec de l'ingestion")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n[STOP] Ingestion interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        logger.error(f"[ERROR] Erreur lors de l'ingestion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
