from fastapi import FastAPI, HTTPException, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import uvicorn
import asyncpg
from collections import deque
from contextlib import asynccontextmanager
from store import PersistentStore
import os
from pathlib import Path
import logging
import httpx
from datetime import datetime
from enum import Enum
import uuid


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("lab-controller")


INCIDENTS_TRIGGERED = Counter('lab_incidents_triggered_total', 'Incidents triggered', ['type'])
ALERTS_RECEIVED = Counter('lab_alerts_received_total', 'Alertes recues d'"'"'Alertmanager', ['alertname', 'severity', 'status'])
INCIDENTS_RESOLVED = Counter('lab_incidents_resolved_total', 'Incidents resolved', ['type'])
INCIDENT_MTTR = Histogram('lab_incident_mttr_seconds', 'Mean Time To Resolve', buckets=[60, 300, 600, 1800, 3600, 7200])
POSTMORTEMS_CREATED = Counter('lab_postmortems_created_total', 'Post-mortems created')
TOIL_IDENTIFIED = Gauge('lab_toil_tasks_identified', 'Toil tasks identified')
AUTOMATION_SAVINGS = Gauge('lab_automation_time_saved_seconds', 'Time saved by automation')

@asynccontextmanager
async def lifespan(_app):
    global db_pool, incidents_db, postmortems_db, toil_tasks_db
    db_pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"], min_size=1, max_size=10, command_timeout=5)
    incidents_db = await PersistentStore(db_pool, "lab.incidents", Incident).load()
    postmortems_db = await PersistentStore(db_pool, "lab.postmortems", PostMortem).load()
    toil_tasks_db = await PersistentStore(db_pool, "lab.toil_tasks", ToilTask).load()
    await init_toil_tasks()
    logger.info("Lab Controller connecte a PostgreSQL")
    yield
    await db_pool.close()

db_pool = None
recent_alerts = deque(maxlen=200)

app = FastAPI(title="Lab Controller", version="1.0.0", docs_url="/api/docs", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class IncidentSeverity(str, Enum):
    P1_CRITICAL = "P1"
    P2_HIGH = "P2"
    P3_MEDIUM = "P3"
    P4_LOW = "P4"

class IncidentStatus(str, Enum):
    TRIGGERED = "triggered"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"

class WitnessRole(str, Enum):
    BACKEND_DEV = "Backend Developer"
    FRONTEND_DEV = "Frontend Developer"
    SRE = "Site Reliability Engineer"
    DBA = "Database Administrator"
    DEVOPS = "DevOps Engineer"

class IncidentType(str, Enum):
    PAYMENT_LATENCY = "payment_latency"
    CATALOG_ERRORS = "catalog_errors"
    DATABASE_SATURATION = "database_saturation"
    CART_UNAVAILABLE = "cart_unavailable"
    USER_AUTH_FAILURE = "user_auth_failure"

class WitnessReport(BaseModel):
    id: str
    role: WitnessRole
    name: str
    observation: str
    timeline_events: List[str]
    suspected_cause: str
    actions_taken: List[str]
    submitted_at: str

class Incident(BaseModel):
    id: str
    type: IncidentType
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    affected_services: List[str]
    timeline: List[dict]
    witness_reports: List[WitnessReport] = []
    triggered_at: str
    resolved_at: Optional[str] = None
    mttr_seconds: Optional[int] = None
    chaos_config: Optional[dict] = None

class PostMortem(BaseModel):
    id: str
    incident_id: str
    title: str
    summary: str
    impact: str
    root_cause: str
    timeline: List[dict]
    lessons_learned: List[str]
    action_items: List[dict]
    created_at: str
    participants: List[str]


    owner: str = ""
    shared_with: str = ""
    status: str = "Brouillon"


    duration: str = ""
    products_affected: str = ""
    percentage_affected: str = ""
    user_impact: str = ""
    detection: str = ""
    resolution: str = ""


    trigger: str = ""
    system_reaction: str = ""
    missing_protections: str = ""
    late_detection: str = ""


    things_that_went_well: List[str] = []
    things_that_went_poorly: List[str] = []
    where_we_got_lucky: List[str] = []

class ToilTask(BaseModel):
    id: str
    name: str
    description: str
    frequency: str
    time_spent_minutes: int
    automatable: bool
    automated: bool = False
    automation_suggestion: Optional[str] = None
    incidents_related: List[str] = []

class TriggerIncidentRequest(BaseModel):
    incident_type: IncidentType
    auto_generate_reports: bool = True


incidents_db: "PersistentStore" = None
postmortems_db: "PersistentStore" = None
toil_tasks_db: "PersistentStore" = None
chaos_enabled: Dict[str, bool] = {}


INCIDENT_SCENARIOS = {
    IncidentType.PAYMENT_LATENCY: {
        "title": "Latence élevée du service de paiement",
        "description": "Les utilisateurs signalent des temps de réponse très lents lors du paiement. Le circuit breaker risque de s'ouvrir.",
        "severity": IncidentSeverity.P1_CRITICAL,
        "affected_services": ["payment-service", "orders-service", "api-gateway"],
        "chaos_config": {
            "service": "payment-service",
            "type": "latency",
            "latency_ms": 3000,
            "error_rate": 0
        },
        "witness_reports_templates": [
            {
                "role": WitnessRole.BACKEND_DEV,
                "name": "Alice Martin",
                "observation": "J'ai remarqué que les logs du payment-service montrent des temps de réponse anormalement élevés. La connexion au provider externe semble être le goulot d'étranglement.",
                "timeline_events": [
                    "14:32 - Première alerte Slack sur latence payment",
                    "14:35 - Vérification des logs, latence > 3s observée",
                    "14:40 - Identification du provider externe comme source"
                ],
                "suspected_cause": "Le provider de paiement externe semble avoir des problèmes de performance. Leurs status page n'indique rien mais nos métriques montrent clairement le problème.",
                "actions_taken": [
                    "Augmenté les timeouts temporairement",
                    "Contacté le support du provider"
                ]
            },
            {
                "role": WitnessRole.SRE,
                "name": "Bob Dupont",
                "observation": "Le circuit breaker a commencé à passer en état HALF-OPEN. Les dashboards Grafana montrent un pic de latence p99 à 5s alors que notre SLO est de 500ms.",
                "timeline_events": [
                    "14:30 - Alerte PagerDuty reçue",
                    "14:33 - Dashboard vérifié, latence p99 = 4.8s",
                    "14:38 - Circuit breaker passé en OPEN",
                    "14:45 - Error budget consommé à 80%"
                ],
                "suspected_cause": "Dégradation du service externe de paiement causant un dépassement de nos SLOs de latence.",
                "actions_taken": [
                    "Vérifié les métriques du circuit breaker",
                    "Préparé le rollback si nécessaire",
                    "Surveillé l'error budget"
                ]
            },
            {
                "role": WitnessRole.FRONTEND_DEV,
                "name": "Charlie Bernard",
                "observation": "Les utilisateurs voient un spinner de chargement pendant plus de 10 secondes sur la page de paiement. Certains abandonnent leur panier.",
                "timeline_events": [
                    "14:35 - Premier ticket support reçu",
                    "14:40 - 15 tickets similaires",
                    "14:50 - Taux d'abandon panier +40%"
                ],
                "suspected_cause": "Le frontend attend la réponse du backend qui est bloqué par le service de paiement.",
                "actions_taken": [
                    "Ajouté un message d'attente pour les utilisateurs",
                    "Préparé une bannière de maintenance si nécessaire"
                ]
            }
        ]
    },
    IncidentType.CATALOG_ERRORS: {
        "title": "Erreurs 500 sur le service Catalogue",
        "description": "Le service catalogue retourne des erreurs 500 de manière intermittente, affectant l'affichage des produits.",
        "severity": IncidentSeverity.P2_HIGH,
        "affected_services": ["catalog-service", "api-gateway"],
        "chaos_config": {
            "service": "catalog-service",
            "type": "error",
            "latency_ms": 0,
            "error_rate": 0.3
        },
        "witness_reports_templates": [
            {
                "role": WitnessRole.BACKEND_DEV,
                "name": "Diana Petit",
                "observation": "Les logs montrent des erreurs de connexion à la base de données. Le pool de connexions semble saturé.",
                "timeline_events": [
                    "10:15 - Premières erreurs 500 dans les logs",
                    "10:20 - Taux d'erreur monte à 30%",
                    "10:25 - Pool de connexions identifié comme saturé"
                ],
                "suspected_cause": "Le pool de connexions à la base de données a atteint sa limite suite à un pic de trafic.",
                "actions_taken": [
                    "Augmenté la taille du pool de connexions",
                    "Ajouté du retry logic"
                ]
            },
            {
                "role": WitnessRole.DBA,
                "name": "Eric Robert",
                "observation": "La base de données montre un nombre anormal de connexions actives. Certaines requêtes semblent bloquées.",
                "timeline_events": [
                    "10:18 - Alerte sur le nombre de connexions",
                    "10:22 - Identification de requêtes bloquées",
                    "10:30 - Kill des requêtes problématiques"
                ],
                "suspected_cause": "Des requêtes longues bloquent les connexions, créant un effet de cascade.",
                "actions_taken": [
                    "Tué les requêtes bloquées",
                    "Augmenté les limites de connexions temporairement"
                ]
            }
        ]
    },
    IncidentType.DATABASE_SATURATION: {
        "title": "Saturation de la base de données",
        "description": "La base de données atteint ses limites de capacité, causant des ralentissements généralisés.",
        "severity": IncidentSeverity.P1_CRITICAL,
        "affected_services": ["catalog-service", "orders-service", "users-service", "api-gateway"],
        "chaos_config": {
            "service": "catalog-service",
            "type": "combined",
            "latency_ms": 2000,
            "error_rate": 0.2
        },
        "witness_reports_templates": [
            {
                "role": WitnessRole.DBA,
                "name": "Eric Robert",
                "observation": "CPU à 98%, I/O disque saturé. Les requêtes les plus simples prennent plusieurs secondes.",
                "timeline_events": [
                    "09:00 - CPU base de données > 90%",
                    "09:05 - I/O wait > 50%",
                    "09:10 - Temps de réponse requêtes > 2s",
                    "09:15 - Décision de scale-up urgent"
                ],
                "suspected_cause": "La campagne marketing a généré 5x plus de trafic que prévu. La base n'était pas dimensionnée pour cette charge.",
                "actions_taken": [
                    "Lancé un scale-up de la base",
                    "Mis en place un cache de requêtes d'urgence",
                    "Désactivé les features non-essentielles"
                ]
            },
            {
                "role": WitnessRole.SRE,
                "name": "Bob Dupont",
                "observation": "Tous les services dépendant de la base montrent des dégradations. L'error budget de plusieurs SLOs est presque épuisé.",
                "timeline_events": [
                    "09:02 - Cascade d'alertes sur tous les services",
                    "09:08 - Error budget latence à 10%",
                    "09:12 - Décision d'incident P1"
                ],
                "suspected_cause": "Sous-dimensionnement de l'infrastructure face au pic de trafic marketing.",
                "actions_taken": [
                    "Escaladé en P1",
                    "Coordonné la réponse entre équipes",
                    "Documenté la timeline"
                ]
            }
        ]
    },
    IncidentType.CART_UNAVAILABLE: {
        "title": "Service Panier indisponible",
        "description": "Le service de gestion des paniers ne répond plus, empêchant les ajouts au panier.",
        "severity": IncidentSeverity.P2_HIGH,
        "affected_services": ["cart-service", "orders-service", "api-gateway"],
        "chaos_config": {
            "service": "cart-service",
            "type": "error",
            "latency_ms": 0,
            "error_rate": 0.8
        },
        "witness_reports_templates": [
            {
                "role": WitnessRole.DEVOPS,
                "name": "François Leroy",
                "observation": "Le pod cart-service redémarre en boucle. Les logs montrent des OOMKilled.",
                "timeline_events": [
                    "16:00 - Premier restart du pod",
                    "16:02 - Deuxième restart, OOMKilled",
                    "16:05 - CrashLoopBackOff"
                ],
                "suspected_cause": "Memory leak dans le service cart, probablement lié au cache Redis qui n'est pas vidé correctement.",
                "actions_taken": [
                    "Augmenté les limites de mémoire",
                    "Forcé le redémarrage avec nouvelles limites",
                    "Ouvert un ticket pour investigation du memory leak"
                ]
            }
        ]
    },
    IncidentType.USER_AUTH_FAILURE: {
        "title": "Échecs d'authentification utilisateurs",
        "description": "Les utilisateurs ne peuvent plus se connecter, le service d'authentification échoue.",
        "severity": IncidentSeverity.P1_CRITICAL,
        "affected_services": ["users-service", "api-gateway"],
        "chaos_config": {
            "service": "users-service",
            "type": "error",
            "latency_ms": 0,
            "error_rate": 0.9
        },
        "witness_reports_templates": [
            {
                "role": WitnessRole.BACKEND_DEV,
                "name": "Alice Martin",
                "observation": "Le service users retourne des erreurs JWT. La clé de signature semble avoir été rotée incorrectement.",
                "timeline_events": [
                    "11:30 - Premières erreurs 401",
                    "11:32 - Taux d'échec login à 90%",
                    "11:35 - Identification problème JWT"
                ],
                "suspected_cause": "Le déploiement de 11h a roté la clé JWT sans déployer la nouvelle clé aux autres services.",
                "actions_taken": [
                    "Identifié le commit problématique",
                    "Préparé le rollback"
                ]
            },
            {
                "role": WitnessRole.SRE,
                "name": "Bob Dupont",
                "observation": "100% des tentatives de login échouent. C'est un incident critique affectant tous les utilisateurs.",
                "timeline_events": [
                    "11:31 - PagerDuty critique",
                    "11:33 - Confirmation impact total",
                    "11:40 - Rollback lancé"
                ],
                "suspected_cause": "Erreur de configuration dans le pipeline de déploiement.",
                "actions_taken": [
                    "Lancé le rollback immédiat",
                    "Coordonné avec l'équipe backend"
                ]
            }
        ]
    }
}


TOIL_TEMPLATES = [
    ToilTask(
        id="toil-001",
        name="Restart manuel des pods en CrashLoopBackOff",
        description="Identifier et redémarrer manuellement les pods qui sont en CrashLoopBackOff",
        frequency="per-incident",
        time_spent_minutes=15,
        automatable=True,
        automation_suggestion="Créer un runbook automatisé avec kubectl qui détecte et restart les pods, avec notification Slack"
    ),
    ToilTask(
        id="toil-002",
        name="Vérification manuelle des logs après incident",
        description="Parcourir les logs de chaque service pour identifier la cause racine",
        frequency="per-incident",
        time_spent_minutes=30,
        automatable=True,
        automation_suggestion="Configurer des requêtes Loki pré-définies avec corrélation automatique par trace_id"
    ),
    ToilTask(
        id="toil-003",
        name="Reset manuel du Circuit Breaker",
        description="Aller manuellement reset le circuit breaker quand le service externe est rétabli",
        frequency="per-incident",
        time_spent_minutes=5,
        automatable=True,
        automation_suggestion="Implémenter un health check automatique qui reset le circuit breaker quand le service est healthy"
    ),
    ToilTask(
        id="toil-004",
        name="Collecte des métriques pour le post-mortem",
        description="Capturer les screenshots des dashboards et exporter les métriques pertinentes",
        frequency="per-incident",
        time_spent_minutes=20,
        automatable=True,
        automation_suggestion="Script qui génère automatiquement un rapport avec les métriques clés de la période de l'incident"
    ),
    ToilTask(
        id="toil-005",
        name="Notification des stakeholders",
        description="Envoyer manuellement des updates par email/Slack aux différentes équipes",
        frequency="per-incident",
        time_spent_minutes=10,
        automatable=True,
        automation_suggestion="Intégrer StatusPage avec mise à jour automatique basée sur les alertes Alertmanager"
    )
]

async def init_toil_tasks():
    for task in TOIL_TEMPLATES:
        if task.id not in toil_tasks_db:
            toil_tasks_db[task.id] = task
    TOIL_IDENTIFIED.set(len(toil_tasks_db))


SERVICE_URLS = {
    "payment-service": os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8084"),
    "catalog-service": os.getenv("CATALOG_SERVICE_URL", "http://catalog-service:8081"),
    "cart-service": os.getenv("CART_SERVICE_URL", "http://cart-service:8082"),
    "orders-service": os.getenv("ORDERS_SERVICE_URL", "http://orders-service:8083"),
    "users-service": os.getenv("USERS_SERVICE_URL", "http://users-service:8085"),
}

async def inject_chaos(service: str, latency_ms: int, error_rate: float):
    logger.info(f"Injecting chaos: {service} - latency={latency_ms}ms, error_rate={error_rate}")
    chaos_enabled[service] = True
    url = SERVICE_URLS.get(service)
    if not url:
        logger.warning(f"Unknown service for chaos injection: {service}")
        return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{url}/api/chaos", json={
                "enabled": True,
                "latency_ms": latency_ms,
                "error_rate": error_rate,
            })
    except Exception as e:
        logger.error(f"Failed to inject chaos on {service}: {e}")

async def stop_chaos(service: str):
    logger.info(f"Stopping chaos: {service}")
    chaos_enabled[service] = False
    url = SERVICE_URLS.get(service)
    if not url:
        logger.warning(f"Unknown service for chaos stop: {service}")
        return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{url}/api/chaos", json={
                "enabled": False,
                "latency_ms": 0,
                "error_rate": 0,
            })
    except Exception as e:
        logger.error(f"Failed to stop chaos on {service}: {e}")


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "lab-controller",
        "active_incidents": len([i for i in incidents_db.values() if i.status != IncidentStatus.RESOLVED]),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/incidents/trigger", response_model=Incident)
async def trigger_incident(request: TriggerIncidentRequest, background_tasks: BackgroundTasks):
    """Déclenche un nouvel incident avec scénario pré-défini"""
    scenario = INCIDENT_SCENARIOS.get(request.incident_type)
    if not scenario:
        raise HTTPException(status_code=400, detail="Unknown incident type")
    
    incident_id = f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8]}"
    
    incident = Incident(
        id=incident_id,
        type=request.incident_type,
        title=scenario["title"],
        description=scenario["description"],
        severity=scenario["severity"],
        status=IncidentStatus.TRIGGERED,
        affected_services=scenario["affected_services"],
        timeline=[{
            "timestamp": datetime.now().isoformat(),
            "event": "Incident triggered",
            "actor": "Lab Controller"
        }],
        triggered_at=datetime.now().isoformat(),
        chaos_config=scenario["chaos_config"]
    )
    

    if request.auto_generate_reports:
        for template in scenario.get("witness_reports_templates", []):
            report = WitnessReport(
                id=f"WR-{str(uuid.uuid4())[:8]}",
                role=template["role"],
                name=template["name"],
                observation=template["observation"],
                timeline_events=template["timeline_events"],
                suspected_cause=template["suspected_cause"],
                actions_taken=template["actions_taken"],
                submitted_at=datetime.now().isoformat()
            )
            incident.witness_reports.append(report)
    
    incidents_db[incident_id] = incident
    

    if scenario["chaos_config"]:
        background_tasks.add_task(
            inject_chaos,
            scenario["chaos_config"]["service"],
            scenario["chaos_config"].get("latency_ms", 0),
            scenario["chaos_config"].get("error_rate", 0)
        )
    
    INCIDENTS_TRIGGERED.labels(type=request.incident_type.value).inc()
    logger.info(f"Incident triggered: {incident_id} - {scenario['title']}")
    
    return incident

@app.post("/api/webhooks/alertmanager")
async def receive_alertmanager_webhook(payload: dict):
    """Recoit les notifications d'Alertmanager et les journalise."""
    alerts = payload.get("alerts", [])
    for alert in alerts:
        labels = alert.get("labels", {})
        name = labels.get("alertname", "unknown")
        severity = labels.get("severity", "unknown")
        status = alert.get("status", "unknown")
        ALERTS_RECEIVED.labels(alertname=name, severity=severity, status=status).inc()
        recent_alerts.append({
            "alertname": name,
            "severity": severity,
            "status": status,
            "service": labels.get("service", labels.get("job", "")),
            "summary": alert.get("annotations", {}).get("summary", ""),
            "starts_at": alert.get("startsAt", ""),
            "received_at": datetime.now().isoformat(),
        })
        logger.info("Alerte %s [%s] %s", name, severity, status)
    return {"received": len(alerts)}


@app.get("/api/alerts")
async def list_recent_alerts(limit: int = 50):
    """Dernieres alertes recues d'Alertmanager."""
    return list(recent_alerts)[-limit:][::-1]


@app.get("/api/incidents", response_model=List[Incident])
async def list_incidents(status: Optional[IncidentStatus] = None):
    """Liste tous les incidents"""
    incidents = list(incidents_db.values())
    if status:
        incidents = [i for i in incidents if i.status == status]
    return sorted(incidents, key=lambda x: x.triggered_at, reverse=True)

@app.get("/api/incidents/{incident_id}", response_model=Incident)
async def get_incident(incident_id: str):
    """Récupère un incident par son ID"""
    if incident_id not in incidents_db:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incidents_db[incident_id]

@app.put("/api/incidents/{incident_id}/status")
async def update_incident_status(incident_id: str, status: IncidentStatus, background_tasks: BackgroundTasks):
    """Met à jour le statut d'un incident"""
    if incident_id not in incidents_db:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    incident = incidents_db[incident_id]
    old_status = incident.status
    incident.status = status
    
    incident.timeline.append({
        "timestamp": datetime.now().isoformat(),
        "event": f"Status changed: {old_status.value} → {status.value}",
        "actor": "User"
    })
    
    if status == IncidentStatus.RESOLVED:
        incident.resolved_at = datetime.now().isoformat()
        triggered = datetime.fromisoformat(incident.triggered_at)
        resolved = datetime.fromisoformat(incident.resolved_at)
        incident.mttr_seconds = int((resolved - triggered).total_seconds())
        
        INCIDENTS_RESOLVED.labels(type=incident.type.value).inc()
        INCIDENT_MTTR.observe(incident.mttr_seconds)
        

        if incident.chaos_config:
            background_tasks.add_task(stop_chaos, incident.chaos_config["service"])
        

        for task in toil_tasks_db.values():
            if incident.id not in task.incidents_related:
                task.incidents_related.append(incident.id)
    
    incidents_db[incident_id] = incident
    logger.info(f"Incident {incident_id} status updated to {status.value}")
    
    return incident

class TimelineEvent(BaseModel):
    event: str
    actor: str = "User"


@app.post("/api/incidents/{incident_id}/timeline")
async def add_timeline_event(incident_id: str, entry: TimelineEvent):
    """Ajoute un événement à la timeline de l'incident"""
    if incident_id not in incidents_db:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    incident = incidents_db[incident_id]
    incident.timeline.append({
        "timestamp": datetime.now().isoformat(),
        "event": entry.event,
        "actor": entry.actor
    })
    
    incidents_db[incident_id] = incident
    return incident


@app.post("/api/postmortems/generate/{incident_id}", response_model=PostMortem)
async def generate_postmortem(incident_id: str):
    """Génère un post-mortem à partir d'un incident et de ses rapports de témoins"""
    if incident_id not in incidents_db:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    incident = incidents_db[incident_id]
    
    if incident.status != IncidentStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Incident must be resolved first")
    

    observations = []
    suspected_causes = []
    all_actions = []
    participants = []
    
    for report in incident.witness_reports:
        observations.append(f"**{report.name} ({report.role.value})**: {report.observation}")
        suspected_causes.append(f"- {report.name}: {report.suspected_cause}")
        all_actions.extend(report.actions_taken)
        participants.append(f"{report.name} ({report.role.value})")
    

    suspicions = "\n".join(suspected_causes) if suspected_causes else ""

    mttr_seconds = incident.mttr_seconds or 0
    mttr_minutes = mttr_seconds // 60
    duration = (f"{mttr_minutes} min {mttr_seconds % 60} s"
                if mttr_minutes else f"{mttr_seconds} s")
    impact = (f"Services affectés: {', '.join(incident.affected_services)}. "
              f"Durée: {duration}. Sévérité: {incident.severity.value}.")

    postmortem_id = f"PM-{incident_id}"

    postmortem = PostMortem(
        id=postmortem_id,
        incident_id=incident_id,
        title=f"Post-Mortem: {incident.title}",
        summary="\n\n".join(observations) if observations else incident.description,

        impact=impact,
        timeline=incident.timeline,
        duration=duration,
        products_affected=", ".join(incident.affected_services),
        created_at=datetime.now().isoformat(),
        participants=participants,
        status="Brouillon",

        root_cause=(f"À compléter. Pistes évoquées par les témoins :\n{suspicions}"
                    if suspicions else "À compléter."),
        lessons_learned=[],
        things_that_went_well=[],
        things_that_went_poorly=[],
        where_we_got_lucky=[],
        action_items=[],
    )
    
    postmortems_db[postmortem_id] = postmortem
    POSTMORTEMS_CREATED.inc()
    
    logger.info(f"Post-mortem generated: {postmortem_id}")
    return postmortem

@app.get("/api/postmortems", response_model=List[PostMortem])
async def list_postmortems():
    """Liste tous les post-mortems"""
    return list(postmortems_db.values())

@app.get("/api/postmortems/{postmortem_id}", response_model=PostMortem)
async def get_postmortem(postmortem_id: str):
    """Récupère un post-mortem par son ID"""
    if postmortem_id not in postmortems_db:
        raise HTTPException(status_code=404, detail="Post-mortem not found")
    return postmortems_db[postmortem_id]

@app.put("/api/postmortems/{postmortem_id}")
async def update_postmortem(postmortem_id: str, updates: dict):
    """Met à jour un post-mortem"""
    if postmortem_id not in postmortems_db:
        raise HTTPException(status_code=404, detail="Post-mortem not found")
    
    postmortem = postmortems_db[postmortem_id]


    EDITABLE = (
        "owner", "shared_with", "status",
        "user_impact", "percentage_affected",
        "detection", "resolution",
        "root_cause", "trigger", "system_reaction",
        "missing_protections", "late_detection",
        "lessons_learned", "things_that_went_well",
        "things_that_went_poorly", "where_we_got_lucky",
        "action_items",
    )
    for field in EDITABLE:
        if field in updates:
            setattr(postmortem, field, updates[field])

    postmortems_db[postmortem_id] = postmortem
    return postmortem


@app.get("/api/toil", response_model=List[ToilTask])
async def list_toil_tasks():
    """Liste toutes les tâches de toil identifiées"""
    return list(toil_tasks_db.values())

@app.get("/api/toil/summary")
async def get_toil_summary():
    """Retourne un résumé du toil"""
    tasks = list(toil_tasks_db.values())
    
    total_time_per_incident = sum(t.time_spent_minutes for t in tasks if t.frequency == "per-incident")
    total_incidents = len(incidents_db)
    
    automatable = [t for t in tasks if t.automatable]
    potential_savings = sum(t.time_spent_minutes for t in automatable)
    
    return {
        "total_toil_tasks": len(tasks),
        "automatable_tasks": len(automatable),
        "time_spent_per_incident_minutes": total_time_per_incident,
        "total_incidents": total_incidents,
        "total_time_spent_minutes": total_time_per_incident * max(total_incidents, 1),
        "potential_automation_savings_minutes": potential_savings * max(total_incidents, 1),
        "recommendations": [t.automation_suggestion for t in automatable if t.automation_suggestion]
    }

@app.post("/api/toil/{task_id}/automate")
async def mark_task_automated(task_id: str):
    """Marque une tâche comme automatisée"""
    if task_id not in toil_tasks_db:
        raise HTTPException(status_code=404, detail="Toil task not found")
    
    task = toil_tasks_db[task_id]
    original_time = task.time_spent_minutes
    task.automated = True
    task.time_spent_minutes = 1
    
    savings = (original_time - 1) * len(task.incidents_related)
    AUTOMATION_SAVINGS.inc(savings * 60)
    
    toil_tasks_db[task_id] = task
    
    return {
        "message": f"Task {task_id} marked as automated",
        "time_saved_per_incident_minutes": original_time - 1,
        "total_incidents_affected": len(task.incidents_related)
    }


@app.get("/api/incident-types")
async def list_incident_types():
    """Liste tous les types d'incidents disponibles"""
    return [
        {
            "type": incident_type.value,
            "title": scenario["title"],
            "description": scenario["description"],
            "severity": scenario["severity"].value,
            "affected_services": scenario["affected_services"]
        }
        for incident_type, scenario in INCIDENT_SCENARIOS.items()
    ]


STATIC_DIR = Path(__file__).parent / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def home():
    return FileResponse(STATIC_DIR / "index.html")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8090"))
    logger.info(f"Starting Lab Controller on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
