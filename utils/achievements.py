import json
from typing import List, Dict
from models.database import Achievement, get_db
from sqlalchemy.exc import IntegrityError

# SVG icons for achievements
BADGE_ICONS = {
    'explorer': '''<svg viewBox="0 0 24 24" width="24" height="24">
        <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-5.5-2.5l7.51-3.49L17.5 6.5 9.99 9.99 6.5 17.5zm5.5-6.6c.61 0 1.1.49 1.1 1.1s-.49 1.1-1.1 1.1-1.1-.49-1.1-1.1.49-1.1 1.1-1.1z"/>
    </svg>''',
    'eco_warrior': '''<svg viewBox="0 0 24 24" width="24" height="24">
        <path fill="currentColor" d="M12 22q-2.075 0-3.9-.788t-3.175-2.137q-1.35-1.35-2.137-3.175T2 12q0-2.075.788-3.9t2.137-3.175q1.35-1.35 3.175-2.137T12 2q2.075 0 3.9.788t3.175 2.137q1.35 1.35 2.138 3.175T22 12q0 2.075-.788 3.9t-2.137 3.175q-1.35 1.35-3.175 2.138T12 22zm0-2q3.35 0 5.675-2.325T20 12q0-3.35-2.325-5.675T12 4Q8.65 4 6.325 6.325T4 12q0 3.35 2.325 5.675T12 20zm0-8z"/>
    </svg>''',
    'community_leader': '''<svg viewBox="0 0 24 24" width="24" height="24">
        <path fill="currentColor" d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/>
    </svg>'''
}

# Define initial achievements
INITIAL_ACHIEVEMENTS = [
    {
        "name": "Explorer I",
        "description": "Discover your first 5 sustainable businesses",
        "icon": BADGE_ICONS['explorer'],
        "criteria": json.dumps({"businesses_viewed": 5}),
        "points": 100,
        "category": "exploration",
        "level": 1
    },
    {
        "name": "Explorer II",
        "description": "Discover 25 sustainable businesses",
        "icon": BADGE_ICONS['explorer'],
        "criteria": json.dumps({"businesses_viewed": 25}),
        "points": 250,
        "category": "exploration",
        "level": 2
    },
    {
        "name": "Eco Warrior I",
        "description": "Find 5 businesses with 90%+ sustainability score",
        "icon": BADGE_ICONS['eco_warrior'],
        "criteria": json.dumps({"high_sustainability_count": 5}),
        "points": 150,
        "category": "sustainability",
        "level": 1
    },
    {
        "name": "Community Leader I",
        "description": "Explore sustainable businesses in 5 different states",
        "icon": BADGE_ICONS['community_leader'],
        "criteria": json.dumps({"states_visited": 5}),
        "points": 200,
        "category": "community",
        "level": 1
    }
]

def initialize_achievements():
    """Initialize achievement data in the database."""
    db = next(get_db())
    for achievement_data in INITIAL_ACHIEVEMENTS:
        try:
            achievement = Achievement(**achievement_data)
            db.add(achievement)
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        except Exception as e:
            db.rollback()
            print(f"Error adding achievement {achievement_data['name']}: {str(e)}")
            continue

def get_all_achievements() -> List[Dict]:
    """Get all available achievements."""
    db = next(get_db())
    achievements = db.query(Achievement).all()
    return [
        {
            "name": a.name,
            "description": a.description,
            "icon": a.icon,
            "points": a.points,
            "category": a.category,
            "level": a.level
        }
        for a in achievements
    ]