# Hospital Staffing - Gestion des plannings hospitaliers

Application web pour la gestion automatisée des plannings de personnel soignant.

## Fonctionnalités

- **Génération automatique de planning** avec algorithme glouton + recuit simulé
- **Gestion des contraintes** :
  - Contraintes dures (obligatoires) : certifications, quotas, chevauchements, préférences dures
  - Contraintes souples (optimisables) : préférences, équité de charge, continuité des soins
- **API REST** avec authentification par token
- **Frontend React** pour l'interface utilisateur

## Architecture

```
├── hospital/          # Backend Django
│   └── products/
│       ├── generator.py      # Algorithme de génération
│       ├── validators.py     # Contraintes dures
│       ├── soft_validators.py # Contraintes souples
│       └── planning_api.py   # Endpoints API
│
└── frontend/         # Frontend React + TypeScript
    └── src/
        ├── api/      # Appels API
        ├── components/ # Composants UI
        └── pages/    # Pages de l'application
```

## Installation

### Backend

```bash
cd hospital
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sur Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo  # Données de démo
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## API

### Authentification

```bash
# Login
POST /api/auth/login/
{
  "username": "admin",
  "password": "admin"
}

# Réponse
{
  "token": "...",
  "staff": {"id": 1, "fullName": "Admin"}
}
```

### Génération de planning

```bash
POST /api/plannings/generate/
{
  "period_start": "2026-04-20",
  "period_end": "2026-04-26",
  "use_optimization": true,
  "max_iterations": 1000
}
```

## Algorithme

### Phase 1 : Glouton (Greedy)
Pour chaque shift, sélectionne le candidat valide avec le score de pénalité le plus bas.

### Phase 2 : Recuit Simulé (Simulated Annealing)
Optimise la solution en échangeant des affectations entre shifts pour minimiser le score global.

## License

MIT
