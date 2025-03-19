import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from models.database import Business, get_db, init_db
from geopy.distance import geodesic
import time

def retry_on_db_error(max_retries=3, delay=1):
    """Decorator for retrying database operations."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except SQLAlchemyError as e:
                    retries += 1
                    if retries == max_retries:
                        raise Exception(f"Database operation failed after {max_retries} retries: {str(e)}")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

@retry_on_db_error()
def init_database():
    """Initialize database with sample data."""
    try:
        # Initialize database schema
        init_db()

        db = next(get_db())

        try:
            # Clear existing data
            db.query(Business).delete()
            db.commit()
            print("Cleared existing data")

            # Load CSV data
            df = pd.read_csv('data/sustainable_fashion_data.csv')
            print(f"Loaded {len(df)} records from CSV")

            # Remove duplicates based on brand_name
            df = df.drop_duplicates(subset=['brand_name'], keep='first')
            print(f"After removing duplicates: {len(df)} records")

            # Track successful insertions
            successful_inserts = 0

            # Insert data into database
            for _, row in df.iterrows():
                try:
                    business = Business(
                        brand_name=row['brand_name'],
                        website=row['website'],
                        description=row['description'],
                        category=row['category'],
                        certifications=row['certifications'].split('|') if pd.notna(row['certifications']) else [],
                        sustainability_score=float(row['sustainability_score']),
                        eco_materials_score=float(row['eco_materials_score']),
                        carbon_footprint=float(row['carbon_footprint']),
                        water_usage=float(row['water_usage']),
                        worker_welfare=float(row['worker_welfare']),
                        year=int(row['year']),
                        latitude=float(row['latitude']),
                        longitude=float(row['longitude']),
                        city=row['city'],
                        state=row['state'],
                        zip_code=row['zip_code']
                    )
                    db.add(business)
                    db.commit()
                    successful_inserts += 1
                except IntegrityError:
                    db.rollback()
                    print(f"Skipping duplicate entry for {row['brand_name']}")
                    continue
                except Exception as e:
                    db.rollback()
                    print(f"Error inserting business {row['brand_name']}: {str(e)}")
                    continue

            print(f"Successfully inserted {successful_inserts} businesses")
            return True

        except Exception as e:
            if 'db' in locals():
                db.rollback()
            raise Exception(f"Error initializing database: {str(e)}")

    except Exception as e:
        print(f"Fatal error in init_database: {str(e)}")
        return False

@retry_on_db_error()
def get_metrics_summary(db_session=None) -> Dict:
    """Get summary statistics for sustainability metrics directly from database."""
    if not db_session:
        db_session = next(get_db())

    try:
        total_businesses = db_session.query(func.count(Business.id)).scalar()
        avg_sustainability = db_session.query(func.avg(Business.sustainability_score)).scalar() or 0
        avg_eco_score = db_session.query(func.avg(Business.eco_materials_score)).scalar() or 0
        states_coverage = db_session.query(func.count(Business.state.distinct())).scalar()

        # Get top categories
        category_counts = (
            db_session.query(
                Business.category,
                func.count(Business.id).label('count')
            )
            .group_by(Business.category)
            .order_by(func.count(Business.id).desc())
            .limit(5)
            .all()
        )
        top_categories = {cat: count for cat, count in category_counts}

        return {
            'total_businesses': total_businesses,
            'avg_sustainability': float(avg_sustainability),
            'top_categories': top_categories,
            'states_coverage': states_coverage,
            'avg_eco_score': float(avg_eco_score)
        }
    except Exception as e:
        raise Exception(f"Error getting metrics summary: {str(e)}")

@retry_on_db_error()
def get_unique_states() -> List[str]:
    """Get list of states from the database."""
    db = next(get_db())
    try:
        states = db.query(Business.state).distinct().all()
        return sorted([state[0] for state in states if state[0]])
    except Exception as e:
        raise Exception(f"Error getting states: {str(e)}")

@retry_on_db_error()
def get_unique_cities() -> List[str]:
    """Get list of unique cities from the database."""
    db = next(get_db())
    try:
        cities = db.query(Business.city).distinct().all()
        return sorted([city[0] for city in cities if city[0]])
    except Exception as e:
        raise Exception(f"Error getting cities: {str(e)}")

@retry_on_db_error()
def get_unique_categories() -> List[str]:
    """Get list of unique business categories."""
    db = next(get_db())
    try:
        categories = db.query(Business.category).distinct().all()
        return sorted([category[0] for category in categories if category[0]])
    except Exception as e:
        raise Exception(f"Error getting categories: {str(e)}")

@retry_on_db_error()
def load_fashion_data(
    page: int = 1,
    per_page: int = 50,
    filters: Dict = None
) -> Tuple[pd.DataFrame, int]:
    """Load and process the sustainable fashion data from database with pagination."""
    try:
        db = next(get_db())
        query = db.query(Business)

        # Apply filters
        if filters:
            if filters.get('category'):
                query = query.filter(Business.category == filters['category'])
            if filters.get('state'):
                query = query.filter(Business.state == filters['state'])
            if filters.get('min_score'):
                query = query.filter(Business.sustainability_score >= filters['min_score'])
            if filters.get('max_score'):
                query = query.filter(Business.sustainability_score <= filters['max_score'])
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                query = query.filter(Business.brand_name.ilike(search_term))

        # Get total count
        total_count = query.count()

        # Apply pagination
        businesses = query.offset((page - 1) * per_page).limit(per_page).all()

        # Convert to DataFrame
        data = []
        for business in businesses:
            data.append({
                'id': business.id,  # Include business ID
                'brand_name': business.brand_name,
                'website': business.website,
                'description': business.description,
                'category': business.category,
                'certifications': business.certifications,
                'sustainability_score': business.sustainability_score,
                'eco_materials_score': business.eco_materials_score,
                'carbon_footprint': business.carbon_footprint,
                'water_usage': business.water_usage,
                'worker_welfare': business.worker_welfare,
                'year': business.year,
                'latitude': business.latitude,
                'longitude': business.longitude,
                'city': business.city,
                'state': business.state,
                'zip_code': business.zip_code
            })

        return pd.DataFrame(data), total_count
    except Exception as e:
        raise Exception(f"Error loading data: {str(e)}")

def get_coordinates_from_city(city: str, state: str) -> Optional[Tuple[float, float]]:
    """Get coordinates for a given city from database."""
    try:
        db = next(get_db())
        business = db.query(Business).filter(
            Business.city == city,
            Business.state == state
        ).first()

        if business:
            return (business.latitude, business.longitude)
        return None
    except Exception:
        return None

def get_nearby_businesses(df: pd.DataFrame, lat: float, lon: float, radius: float) -> pd.DataFrame:
    """Get businesses within specified radius (miles) of given coordinates."""
    if df.empty:
        return pd.DataFrame()

    # Convert radius from miles to kilometers
    radius_km = radius * 1.60934

    # Calculate distances
    df['distance'] = df.apply(
        lambda row: geodesic((lat, lon), (row['latitude'], row['longitude'])).miles,
        axis=1
    )

    # Filter by radius and sort by distance
    nearby = df[df['distance'] <= radius].copy()
    if not nearby.empty:
        nearby = nearby.sort_values('distance')

    return nearby

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula."""
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))

    return R * c