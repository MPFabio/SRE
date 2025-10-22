#!/usr/bin/env python3
"""
Application Flask pour la présentation des post-mortems SRE
Interface web pour visualiser les post-mortems avec un format structuré
"""

from flask import Flask, render_template, jsonify, request
import json
import os
from datetime import datetime
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
POSTMORTEM_DIR = "data/postmortems"
TEMPLATE_DIR = "templates"

def load_postmortem(postmortem_id):
    """Charge un post-mortem depuis le fichier JSON"""
    try:
        file_path = os.path.join(POSTMORTEM_DIR, f"{postmortem_id}.json")
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Post-mortem {postmortem_id} non trouvé")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de parsing JSON pour {postmortem_id}: {e}")
        return None

def list_postmortems():
    """Liste tous les post-mortems disponibles"""
    postmortems = []
    if os.path.exists(POSTMORTEM_DIR):
        for filename in os.listdir(POSTMORTEM_DIR):
            if filename.endswith('.json'):
                postmortem_id = filename[:-5]  # Enlever .json
                try:
                    postmortem = load_postmortem(postmortem_id)
                    if postmortem:
                        postmortems.append({
                            'id': postmortem_id,
                            'title': postmortem.get('title', 'Sans titre'),
                            'incident_date': postmortem.get('incident_date', ''),
                            'status': postmortem.get('status', 'Brouillon'),
                            'published': postmortem.get('published', '')
                        })
                except Exception as e:
                    logger.error(f"Erreur lors du chargement de {postmortem_id}: {e}")
    return sorted(postmortems, key=lambda x: x.get('incident_date', ''), reverse=True)

@app.route('/')
def index():
    """Page d'accueil avec la liste des post-mortems"""
    postmortems = list_postmortems()
    return render_template('index.html', postmortems=postmortems)

@app.route('/postmortem/<postmortem_id>')
def view_postmortem(postmortem_id):
    """Page de visualisation d'un post-mortem spécifique"""
    postmortem = load_postmortem(postmortem_id)
    if not postmortem:
        return render_template('error.html', 
                             message=f"Post-mortem '{postmortem_id}' non trouvé"), 404
    
    return render_template('postmortem.html', postmortem=postmortem)

@app.route('/api/postmortems')
def api_list_postmortems():
    """API pour lister les post-mortems"""
    postmortems = list_postmortems()
    return jsonify(postmortems)

@app.route('/api/postmortem/<postmortem_id>')
def api_get_postmortem(postmortem_id):
    """API pour récupérer un post-mortem spécifique"""
    postmortem = load_postmortem(postmortem_id)
    if not postmortem:
        return jsonify({'error': 'Post-mortem non trouvé'}), 404
    return jsonify(postmortem)

@app.route('/create')
def create_postmortem():
    """Page de création d'un nouveau post-mortem"""
    return render_template('create.html')

@app.route('/api/create', methods=['POST'])
def api_create_postmortem():
    """API pour créer un nouveau post-mortem"""
    try:
        data = request.get_json()
        
        # Générer un ID unique basé sur le timestamp
        postmortem_id = f"incident_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Ajouter des métadonnées
        data['created_at'] = datetime.now().isoformat()
        data['id'] = postmortem_id
        
        # Sauvegarder le fichier
        os.makedirs(POSTMORTEM_DIR, exist_ok=True)
        file_path = os.path.join(POSTMORTEM_DIR, f"{postmortem_id}.json")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return jsonify({'success': True, 'id': postmortem_id})
    
    except Exception as e:
        logger.error(f"Erreur lors de la création du post-mortem: {e}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', message="Page non trouvée"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', message="Erreur interne du serveur"), 500

if __name__ == '__main__':
    # Créer les répertoires nécessaires
    os.makedirs(POSTMORTEM_DIR, exist_ok=True)
    os.makedirs(TEMPLATE_DIR, exist_ok=True)
    
    # Démarrer l'application
    app.run(host='0.0.0.0', port=5000, debug=True)
