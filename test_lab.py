#!/usr/bin/env python3
"""
Script de test pour vérifier le bon fonctionnement du Lab SRE
"""

import requests
import time
import json
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LabTester:
    """Testeur pour le Lab SRE"""
    
    def __init__(self):
        self.service_url = "http://localhost:30000"
        self.splunk_url = "http://localhost:8000"
        self.otel_url = "http://localhost:8889"
        
    def test_service_health(self):
        """Teste la santé du service URL Shortener"""
        logger.info("🔍 Test de la santé du service...")
        
        try:
            response = requests.get(f"{self.service_url}/health", timeout=10)
            if response.status_code == 200:
                logger.info("[SUCCESS] Service en bonne santé")
                return True
            else:
                logger.error(f"[ERROR] Service retourne {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"[ERROR] Erreur de connexion au service: {e}")
            return False
    
    def test_url_shortening(self):
        """Teste la fonctionnalité de raccourcissement d'URL"""
        logger.info("🔗 Test du raccourcissement d'URL...")
        
        try:
            # Test de création d'URL courte
            test_url = "https://www.example.com/test"
            response = requests.post(
                f"{self.service_url}/shorten",
                params={'url': test_url},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                short_code = data.get('short_code')
                logger.info(f"[SUCCESS] URL créée: {short_code}")
                
                # Test de redirection
                redirect_response = requests.get(
                    f"{self.service_url}/{short_code}",
                    allow_redirects=False,
                    timeout=10
                )
                
                if redirect_response.status_code in [301, 302, 307, 308]:
                    logger.info("[SUCCESS] Redirection fonctionne")
                    return True
                else:
                    logger.error(f"[ERROR] Redirection échouée: {redirect_response.status_code}")
                    return False
            else:
                logger.error(f"[ERROR] Création d'URL échouée: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"[ERROR] Erreur lors du test d'URL: {e}")
            return False
    
    def test_metrics_endpoint(self):
        """Teste l'endpoint des métriques"""
        logger.info("[INFO] Test de l'endpoint des métriques...")
        
        try:
            response = requests.get(f"{self.service_url}/metrics", timeout=10)
            if response.status_code == 200:
                metrics = response.text
                if "http_requests_total" in metrics:
                    logger.info("[SUCCESS] Métriques disponibles")
                    return True
                else:
                    logger.warning("[WARN] Métriques incomplètes")
                    return False
            else:
                logger.error(f"[ERROR] Métriques inaccessibles: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"[ERROR] Erreur lors du test des métriques: {e}")
            return False
    
    def test_splunk_connection(self):
        """Teste la connexion à Splunk"""
        logger.info("🔍 Test de la connexion à Splunk...")
        
        try:
            response = requests.get(f"{self.splunk_url}/services/server/info", timeout=10)
            if response.status_code == 200:
                logger.info("[SUCCESS] Splunk accessible")
                return True
            else:
                logger.error(f"[ERROR] Splunk retourne {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"[ERROR] Erreur de connexion à Splunk: {e}")
            return False
    
    def test_otel_collector(self):
        """Teste l'OpenTelemetry Collector"""
        logger.info("🔍 Test de l'OpenTelemetry Collector...")
        
        try:
            response = requests.get(f"{self.otel_url}/metrics", timeout=10)
            if response.status_code == 200:
                logger.info("[SUCCESS] OpenTelemetry Collector accessible")
                return True
            else:
                logger.error(f"[ERROR] OpenTelemetry Collector retourne {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"[ERROR] Erreur de connexion à OpenTelemetry: {e}")
            return False
    
    def test_traffic_generation(self):
        """Teste la génération de trafic"""
        logger.info("🚦 Test de la génération de trafic...")
        
        try:
            # Génère quelques requêtes de test
            for i in range(5):
                test_url = f"https://www.test{i}.com"
                response = requests.post(
                    f"{self.service_url}/shorten",
                    params={'url': test_url},
                    timeout=5
                )
                if response.status_code != 200:
                    logger.warning(f"[WARN] Requête {i+1} échouée: {response.status_code}")
                time.sleep(0.1)
            
            logger.info("[SUCCESS] Génération de trafic testée")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Erreur lors du test de trafic: {e}")
            return False
    
    def run_all_tests(self):
        """Exécute tous les tests"""
        logger.info("🧪 Démarrage des tests du Lab SRE...")
        print("="*60)
        
        tests = [
            ("Service Health", self.test_service_health),
            ("URL Shortening", self.test_url_shortening),
            ("Metrics Endpoint", self.test_metrics_endpoint),
            ("Splunk Connection", self.test_splunk_connection),
            ("OpenTelemetry Collector", self.test_otel_collector),
            ("Traffic Generation", self.test_traffic_generation)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"\n🔍 {test_name}...")
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                logger.error(f"[ERROR] Erreur dans {test_name}: {e}")
                results.append((test_name, False))
        
        # Affiche le résumé
        print("\n" + "="*60)
        print("[INFO] RÉSUMÉ DES TESTS")
        print("="*60)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "[SUCCESS] PASS" if result else "[ERROR] FAIL"
            print(f"{status} {test_name}")
            if result:
                passed += 1
        
        print(f"\nRésultat: {passed}/{total} tests réussis")
        
        if passed == total:
            logger.info("[SUCCESS] Tous les tests sont passés! Le lab est opérationnel.")
            return True
        else:
            logger.warning(f"[WARN] {total - passed} test(s) ont échoué. Vérifiez la configuration.")
            return False

def main():
    """Fonction principale"""
    print("🧪 Testeur du Lab SRE")
    print("====================")
    
    tester = LabTester()
    
    try:
        success = tester.run_all_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n[INFO] Tests interrompus par l'utilisateur")
        exit(1)
    except Exception as e:
        logger.error(f"[ERROR] Erreur lors des tests: {e}")
        exit(1)

if __name__ == "__main__":
    main()
