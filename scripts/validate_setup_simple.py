#!/usr/bin/env python3
"""
Script de validation de la configuration du Lab SRE (version simple)
Vérifie que tous les fichiers et configurations sont corrects
"""

import os
import json
import sys

def check_file_exists(file_path, description):
    """Vérifie qu'un fichier existe"""
    if os.path.exists(file_path):
        print(f"[OK] {description}: {file_path}")
        return True
    else:
        print(f"[FAIL] {description}: {file_path} (MANQUANT)")
        return False

def check_json_file(file_path, description):
    """Vérifie qu'un fichier JSON est valide"""
    if not os.path.exists(file_path):
        print(f"[FAIL] {description}: {file_path} (MANQUANT)")
        return False
    
    try:
        with open(file_path, 'r') as f:
            json.load(f)
        print(f"[OK] {description}: {file_path} (JSON valide)")
        return True
    except json.JSONDecodeError as e:
        print(f"[FAIL] {description}: {file_path} (JSON invalide: {e})")
        return False

def check_directory_structure():
    """Vérifie la structure des dossiers"""
    print("Verification de la structure des dossiers...")
    
    required_dirs = [
        "kind",
        "kind/manifests",
        "data",
        "data/logs",
        "data/metrics", 
        "data/traces",
        "simulator",
        "ingest",
        "incident",
        "automation",
        "sre",
        "exercises"
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"[OK] Dossier: {dir_path}")
        else:
            print(f"[FAIL] Dossier manquant: {dir_path}")
            all_exist = False
    
    return all_exist

def check_required_files():
    """Vérifie les fichiers requis"""
    print("\nVerification des fichiers requis...")
    
    required_files = [
        ("docker-compose.yml", "Configuration Docker Compose"),
        ("README.md", "Documentation principale"),
        ("start_lab.sh", "Script de demarrage"),
        ("test_lab.py", "Script de test"),
        ("requirements.txt", "Dependances Python"),
        ("config.json", "Configuration du lab"),
        ("kind/kind-config.yaml", "Configuration KinD"),
        ("kind/setup.sh", "Script de setup KinD"),
        ("kind/manifests/url-shortener-deployment.yaml", "Deploiement URL Shortener"),
        ("kind/manifests/otel-collector-deployment.yaml", "Deploiement OpenTelemetry"),
        ("kind/manifests/otel-collector-config.yaml", "Configuration OpenTelemetry"),
        ("simulator/traffic_generator.py", "Generateur de trafic"),
        ("ingest/ingest_to_splunk.py", "Script d'ingestion"),
        ("incident/trigger_failure.sh", "Script de simulation d'incident"),
        ("incident/fix_failure.sh", "Script de reparation"),
        ("incident/postmortem_template.md", "Template de post-mortem"),
        ("automation/toil_reduction.sh", "Script d'automatisation"),
        ("sre/slo_config.json", "Configuration des SLOs"),
        ("sre/burn_rate_calc.py", "Calculateur de burn rate"),
        ("sre/error_budget_tracker.py", "Suivi de l'error budget"),
        ("exercises/README.md", "Documentation des exercices")
    ]
    
    all_exist = True
    for file_path, description in required_files:
        if not check_file_exists(file_path, description):
            all_exist = False
    
    return all_exist

def check_configuration_files():
    """Vérifie les fichiers de configuration"""
    print("\nVerification des fichiers de configuration...")
    
    config_files = [
        ("sre/slo_config.json", "Configuration des SLOs"),
        ("config.json", "Configuration du lab")
    ]
    
    all_valid = True
    for file_path, description in config_files:
        if not check_json_file(file_path, description):
            all_valid = False
    
    return all_valid

def main():
    """Fonction principale de validation"""
    print("VALIDATION DU LAB SRE")
    print("=" * 50)
    
    # Vérifie qu'on est dans le bon répertoire
    if not os.path.exists("docker-compose.yml"):
        print("[FAIL] Erreur: Executez ce script depuis le repertoire racine du lab SRE")
        sys.exit(1)
    
    # Effectue toutes les vérifications
    checks = [
        ("Structure des dossiers", check_directory_structure),
        ("Fichiers requis", check_required_files),
        ("Fichiers de configuration", check_configuration_files)
    ]
    
    results = []
    for check_name, check_func in checks:
        print(f"\n{check_name}...")
        result = check_func()
        results.append((check_name, result))
    
    # Affiche le résumé
    print("\n" + "=" * 50)
    print("RESUME DE LA VALIDATION")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for check_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {check_name}")
        if result:
            passed += 1
    
    print(f"\nResultat: {passed}/{total} verifications reussies")
    
    if passed == total:
        print("\nLe lab SRE est correctement configure!")
        print("\nProchaines etapes:")
        print("  1. Executez: ./start_lab.sh")
        print("  2. Testez avec: python3 test_lab.py")
        print("  3. Consultez: exercises/README.md")
        return True
    else:
        print(f"\n{total - passed} verification(s) ont echoue.")
        print("Veuillez corriger les problemes avant de continuer.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nValidation interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\nErreur lors de la validation: {e}")
        sys.exit(1)
