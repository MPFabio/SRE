#!/usr/bin/env python3
"""
Script pour copier les post-mortems locaux dans le déploiement Kubernetes
"""

import os
import json

def copy_postmortem_files():
    """Copie les fichiers post-mortem locaux dans le déploiement"""
    
    # Lire les fichiers post-mortem locaux
    postmortem_dir = "postmortem/data/postmortems"
    files = []
    
    if os.path.exists(postmortem_dir):
        for filename in os.listdir(postmortem_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(postmortem_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    files.append((filename, content))
    
    # Générer le code pour le déploiement
    print("# Copier les post-mortems EXACTS de votre app locale")
    for filename, content in files:
        print(f"cat > /app/data/postmortems/{filename} << 'EOF'")
        print(content)
        print("EOF")
        print()

if __name__ == "__main__":
    copy_postmortem_files()
