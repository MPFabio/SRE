#!/usr/bin/env python3
"""
Générateur de trafic pour le lab SRE
Simule un trafic réaliste avec des patterns de distribution variés
"""

import requests
import time
import random
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import argparse
import sys
from dataclasses import dataclass
import numpy as np

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TrafficConfig:
    """Configuration du trafic simulé"""
    base_url: str = "http://localhost:30000"
    duration_minutes: int = 60
    requests_per_minute: int = 100
    error_rate: float = 0.01  # 1% d'erreurs
    latency_p95: float = 0.5  # 500ms P95
    latency_p99: float = 2.0  # 2s P99
    
    # URLs de test
    test_urls: List[str] = None
    
    def __post_init__(self):
        if self.test_urls is None:
            self.test_urls = [
                "https://www.google.com",
                "https://www.github.com",
                "https://www.stackoverflow.com",
                "https://www.reddit.com",
                "https://www.wikipedia.org",
                "https://www.youtube.com",
                "https://www.amazon.com",
                "https://www.netflix.com",
                "https://www.spotify.com",
                "https://www.twitter.com"
            ]

class TrafficGenerator:
    """Générateur de trafic avec patterns réalistes"""
    
    def __init__(self, config: TrafficConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SRE-Lab-TrafficGenerator/1.0'
        })
        
        # Statistiques
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'created_urls': [],
            'redirected_urls': []
        }
    
    def generate_latency(self) -> float:
        """Génère une latence réaliste basée sur une distribution Pareto"""
        # Distribution Pareto pour simuler des latences réalistes
        # avec quelques requêtes très lentes
        alpha = 1.5
        xm = 0.1  # Valeur minimale
        
        # Génère une valeur Pareto
        pareto_value = xm * (random.random() ** (-1/alpha) - 1)
        
        # Applique des limites réalistes
        return min(max(pareto_value, 0.01), 10.0)
    
    def should_fail(self) -> bool:
        """Détermine si une requête doit échouer"""
        return random.random() < self.config.error_rate
    
    def simulate_error(self, response_time: float) -> bool:
        """Simule différents types d'erreurs"""
        error_type = random.choice([
            'timeout',      # Timeout
            'server_error', # 5xx
            'client_error', # 4xx
            'network_error' # Erreur réseau
        ])
        
        if error_type == 'timeout':
            # Simule un timeout en attendant plus longtemps
            time.sleep(response_time * 2)
            return True
        elif error_type == 'server_error':
            # Simule une erreur 500
            return True
        elif error_type == 'client_error':
            # Simule une erreur 400
            return True
        else:  # network_error
            # Simule une erreur réseau
            return True
    
    def create_short_url(self, original_url: str) -> Dict:
        """Crée une URL courte"""
        try:
            response = self.session.post(
                f"{self.config.base_url}/shorten",
                params={'url': original_url},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.stats['created_urls'].append(data['short_code'])
                return data
            else:
                logger.warning(f"Erreur création URL: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur réseau lors de la création: {e}")
            return None
    
    def redirect_url(self, short_code: str) -> bool:
        """Redirige vers l'URL courte"""
        try:
            response = self.session.get(
                f"{self.config.base_url}/{short_code}",
                timeout=10,
                allow_redirects=False  # On ne suit pas les redirections
            )
            
            if response.status_code in [301, 302, 307, 308]:
                self.stats['redirected_urls'].append(short_code)
                return True
            else:
                logger.warning(f"Redirection échouée: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur réseau lors de la redirection: {e}")
            return False
    
    def generate_traffic_pattern(self) -> List[float]:
        """Génère un pattern de trafic réaliste (plus de trafic en journée)"""
        # Pattern sinusoïdal pour simuler l'activité diurne
        # Plus de trafic entre 9h et 17h
        now = datetime.now()
        hour = now.hour
        
        # Facteur multiplicatif basé sur l'heure
        if 9 <= hour <= 17:
            multiplier = 1.5  # Heures de pointe
        elif 18 <= hour <= 22:
            multiplier = 1.2  # Soirée
        else:
            multiplier = 0.3  # Nuit/tôt le matin
        
        # Ajoute de la variabilité
        noise = random.uniform(0.8, 1.2)
        
        return self.config.requests_per_minute * multiplier * noise
    
    def run_simulation(self):
        """Lance la simulation de trafic"""
        logger.info(f"[INFO] Démarrage de la simulation de trafic")
        logger.info(f"   Durée: {self.config.duration_minutes} minutes")
        logger.info(f"   RPS moyen: {self.config.requests_per_minute}")
        logger.info(f"   Taux d'erreur: {self.config.error_rate * 100:.1f}%")
        
        start_time = time.time()
        end_time = start_time + (self.config.duration_minutes * 60)
        
        # Phase 1: Création d'URLs (30% du trafic)
        logger.info("📝 Phase 1: Création d'URLs...")
        url_creation_phase = end_time - (self.config.duration_minutes * 60 * 0.7)
        
        while time.time() < url_creation_phase:
            if time.time() >= end_time:
                break
                
            # Génère le pattern de trafic
            requests_per_second = self.generate_traffic_pattern() / 60
            
            # Crée des URLs
            for _ in range(int(requests_per_second)):
                if time.time() >= url_creation_phase:
                    break
                    
                original_url = random.choice(self.config.test_urls)
                response_time = self.generate_latency()
                
                # Simule une erreur si nécessaire
                if self.should_fail() and self.simulate_error(response_time):
                    self.stats['failed_requests'] += 1
                    logger.debug("[ERROR] Erreur simulée lors de la création")
                else:
                    # Crée l'URL
                    time.sleep(response_time)
                    result = self.create_short_url(original_url)
                    if result:
                        self.stats['successful_requests'] += 1
                    else:
                        self.stats['failed_requests'] += 1
                
                self.stats['total_requests'] += 1
                self.stats['response_times'].append(response_time)
            
            time.sleep(1)  # Pause d'une seconde
        
        # Phase 2: Redirections (70% du trafic)
        logger.info("🔗 Phase 2: Redirections...")
        
        while time.time() < end_time:
            # Génère le pattern de trafic
            requests_per_second = self.generate_traffic_pattern() / 60
            
            # Redirige vers des URLs existantes
            for _ in range(int(requests_per_second)):
                if time.time() >= end_time:
                    break
                    
                if self.stats['created_urls']:
                    short_code = random.choice(self.stats['created_urls'])
                    response_time = self.generate_latency()
                    
                    # Simule une erreur si nécessaire
                    if self.should_fail() and self.simulate_error(response_time):
                        self.stats['failed_requests'] += 1
                        logger.debug("[ERROR] Erreur simulée lors de la redirection")
                    else:
                        # Redirige
                        time.sleep(response_time)
                        if self.redirect_url(short_code):
                            self.stats['successful_requests'] += 1
                        else:
                            self.stats['failed_requests'] += 1
                    
                    self.stats['total_requests'] += 1
                    self.stats['response_times'].append(response_time)
            
            time.sleep(1)  # Pause d'une seconde
        
        # Affiche les statistiques finales
        self.print_statistics()
    
    def print_statistics(self):
        """Affiche les statistiques de la simulation"""
        if not self.stats['response_times']:
            logger.warning("Aucune donnée de latence disponible")
            return
        
        response_times = np.array(self.stats['response_times'])
        
        print("\n" + "="*60)
        print("📊 STATISTIQUES DE LA SIMULATION")
        print("="*60)
        print(f"Total des requêtes: {self.stats['total_requests']}")
        print(f"Requêtes réussies: {self.stats['successful_requests']}")
        print(f"Requêtes échouées: {self.stats['failed_requests']}")
        print(f"Taux de succès: {(self.stats['successful_requests'] / self.stats['total_requests'] * 100):.2f}%")
        print(f"URLs créées: {len(self.stats['created_urls'])}")
        print(f"Redirections: {len(self.stats['redirected_urls'])}")
        print()
        print("📈 LATENCE:")
        print(f"  Moyenne: {np.mean(response_times):.3f}s")
        print(f"  P50: {np.percentile(response_times, 50):.3f}s")
        print(f"  P95: {np.percentile(response_times, 95):.3f}s")
        print(f"  P99: {np.percentile(response_times, 99):.3f}s")
        print(f"  Max: {np.max(response_times):.3f}s")
        print("="*60)

def main():
    parser = argparse.ArgumentParser(description='Générateur de trafic SRE Lab')
    parser.add_argument('--url', default='http://localhost:30000', 
                       help='URL de base du service (défaut: http://localhost:30000)')
    parser.add_argument('--duration', type=int, default=60,
                       help='Durée en minutes (défaut: 60)')
    parser.add_argument('--rpm', type=int, default=100,
                       help='Requêtes par minute (défaut: 100)')
    parser.add_argument('--error-rate', type=float, default=0.01,
                       help='Taux d\'erreur (défaut: 0.01)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Mode verbeux')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    config = TrafficConfig(
        base_url=args.url,
        duration_minutes=args.duration,
        requests_per_minute=args.rpm,
        error_rate=args.error_rate
    )
    
    generator = TrafficGenerator(config)
    
    try:
        generator.run_simulation()
    except KeyboardInterrupt:
        logger.info("\n[STOP] Simulation interrompue par l'utilisateur")
        generator.print_statistics()
    except Exception as e:
        logger.error(f"[ERROR] Erreur lors de la simulation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
