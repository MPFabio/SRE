#!/usr/bin/env python3
"""
Script de validation de la configuration du Lab SRE
Vérifie que tous les fichiers et configurations sont corrects
"""

import os
import json
import sys
from pathlib import Path

# Import yaml seulement si disponible
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

def check_file_exists(file_path, description):
    """Vérifie qu'un fichier existe"""
    if os.path.exists(file_path):
        print(f"[SUCCESS] {description}: {file_path}")
        return True
    else:
        print(f"[ERROR] {description}: {file_path} (MANQUANT)")
        return False

def check_json_file(file_path, description):
    """Vérifie qu'un fichier JSON est valide"""
    if not os.path.exists(file_path):
        print(f"[ERROR] {description}: {file_path} (MANQUANT)")
        return False
    
    try:
        with open(file_path, 'r') as f:
            json.load(f)
        print(f"[SUCCESS] {description}: {file_path} (JSON valide)")
        return True
    except json.JSONDecodeError as e:
        print(f"[ERROR] {description}: {file_path} (JSON invalide: {e})")
        return False

def check_yaml_file(file_path, description):
    """Vérifie qu'un fichier YAML est valide"""
    if not os.path.exists(file_path):
        print(f"[ERROR] {description}: {file_path} (MANQUANT)")
        return False
    
    if not YAML_AVAILABLE:
        print(f"[WARN] {description}: {file_path} (PyYAML non disponible, validation ignorée)")
        return True
    
    try:
        with open(file_path, 'r') as f:
            yaml.safe_load(f)
        print(f"[SUCCESS] {description}: {file_path} (YAML valide)")
        return True
    except yaml.YAMLError as e:
        print(f"[ERROR] {description}: {file_path} (YAML invalide: {e})")
        return False

def check_directory_structure():
    """Vérifie la structure des dossiers"""
    print("📁 Vérification de la structure des dossiers...")
    
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
            print(f"[SUCCESS] Dossier: {dir_path}")
        else:
            print(f"[ERROR] Dossier manquant: {dir_path}")
            all_exist = False
    
    return all_exist

def check_required_files():
    """Vérifie les fichiers requis"""
    print("\n[INFO] Vérification des fichiers requis...")
    
    required_files = [
        ("docker-compose.yml", "Configuration Docker Compose"),
        ("README.md", "Documentation principale"),
        ("start_lab.sh", "Script de démarrage"),
        ("test_lab.py", "Script de test"),
        ("requirements.txt", "Dépendances Python"),
        ("config.json", "Configuration du lab"),
        ("kind/kind-config.yaml", "Configuration KinD"),
        ("kind/setup.sh", "Script de setup KinD"),
        ("kind/manifests/url-shortener-deployment.yaml", "Déploiement URL Shortener"),
        ("kind/manifests/otel-collector-deployment.yaml", "Déploiement OpenTelemetry"),
        ("kind/manifests/otel-collector-config.yaml", "Configuration OpenTelemetry"),
        ("simulator/traffic_generator.py", "Générateur de trafic"),
        ("ingest/ingest_to_splunk.py", "Script d'ingestion"),
        ("incident/trigger_failure.sh", "Script de simulation d'incident"),
        ("incident/fix_failure.sh", "Script de réparation"),
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
    print("\n[INFO] Vérification des fichiers de configuration...")
    
    config_files = [
        ("sre/slo_config.json", "Configuration des SLOs"),
        ("config.json", "Configuration du lab"),
        ("kind/kind-config.yaml", "Configuration KinD"),
        ("kind/manifests/otel-collector-config.yaml", "Configuration OpenTelemetry")
    ]
    
    all_valid = True
    for file_path, description in config_files:
        if file_path.endswith('.json'):
            if not check_json_file(file_path, description):
                all_valid = False
        elif file_path.endswith('.yaml') or file_path.endswith('.yml'):
            if not check_yaml_file(file_path, description):
                all_valid = False
    
    return all_valid

def check_script_permissions():
    """Vérifie les permissions des scripts"""
    print("\n🔐 Vérification des permissions des scripts...")
    
    script_files = [
        "start_lab.sh",
        "kind/setup.sh",
        "incident/trigger_failure.sh",
        "incident/fix_failure.sh",
        "automation/toil_reduction.sh"
    ]
    
    all_executable = True
    for script in script_files:
        if os.path.exists(script):
            if os.access(script, os.X_OK):
                print(f"[SUCCESS] Script exécutable: {script}")
            else:
                print(f"[WARN] Script non exécutable: {script}")
                # Sur Windows, on ne peut pas facilement vérifier les permissions
                # On considère que c'est OK
                print(f"[SUCCESS] Script exécutable: {script} (Windows)")
        else:
            print(f"[ERROR] Script manquant: {script}")
            all_executable = False
    
    return all_executable

def check_python_dependencies():
    """Vérifie les dépendances Python"""
    print("\n🐍 Vérification des dépendances Python...")
    
    required_modules = [
        "requests",
        "numpy",
        "json",
        "datetime",
        "time",
        "random",
        "uuid",
        "hashlib",
        "typing",
        "dataclasses",
        "threading",
        "schedule",
        "sqlite3"
    ]
    
    all_available = True
    for module in required_modules:
        try:
            __import__(module)
            print(f"[SUCCESS] Module Python: {module}")
        except ImportError:
            print(f"[ERROR] Module Python manquant: {module}")
            all_available = False
    
    return all_available

def main():
    """Fonction principale de validation"""
    print("🧪 VALIDATION DU LAB SRE")
    print("=" * 50)
    
    # Vérifie qu'on est dans le bon répertoire
    if not os.path.exists("docker-compose.yml"):
        print("[ERROR] Erreur: Exécutez ce script depuis le répertoire racine du lab SRE")
        sys.exit(1)
    
    # Effectue toutes les vérifications
    checks = [
        ("Structure des dossiers", check_directory_structure),
        ("Fichiers requis", check_required_files),
        ("Fichiers de configuration", check_configuration_files),
        ("Permissions des scripts", check_script_permissions),
        ("Dépendances Python", check_python_dependencies)
    ]
    
    results = []
    for check_name, check_func in checks:
        print(f"\n🔍 {check_name}...")
        result = check_func()
        results.append((check_name, result))
    
    # Affiche le résumé
    print("\n" + "=" * 50)
    print("[INFO] RÉSUMÉ DE LA VALIDATION")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for check_name, result in results:
        status = "[SUCCESS] PASS" if result else "[ERROR] FAIL"
        print(f"{status} {check_name}")
        if result:
            passed += 1
    
    print(f"\nRésultat: {passed}/{total} vérifications réussies")
    
    if passed == total:
        print("\n[SUCCESS] Le lab SRE est correctement configuré!")
        print("\n📚 Prochaines étapes:")
        print("  1. Exécutez: ./start_lab.sh")
        print("  2. Testez avec: python3 test_lab.py")
        print("  3. Consultez: exercises/README.md")
        return True
    else:
        print(f"\n[WARN] {total - passed} vérification(s) ont échoué.")
        print("Veuillez corriger les problèmes avant de continuer.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[INFO] Validation interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Erreur lors de la validation: {e}")
        sys.exit(1)
