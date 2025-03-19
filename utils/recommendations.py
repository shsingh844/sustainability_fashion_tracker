import os
import json
import numpy as np
from typing import List, Dict
from datetime import datetime, timedelta
from sqlalchemy import desc, func
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from models.database import Business, UserInteraction, get_db
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NumpyJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy types"""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

# Create recommendation prompt template
recommendation_prompt = ChatPromptTemplate.from_template("""
You are a sustainable business advisor helping users discover and support sustainable fashion businesses.
Based on the following user interaction data, generate personalized recommendations.

Recent Interactions:
{interaction_history}

User's Interests:
- Most viewed categories: {most_viewed_categories}
- View counts by category: {category_counts}
- Recently searched states: {states_searched}
- Average sustainability score of viewed businesses: {avg_sustainability_score}

Return a JSON object with three types of recommendations:
1. Business recommendations based on their viewing patterns
2. Sustainability tips based on the types of businesses they view
3. New categories they might be interested in exploring

Response must be a valid JSON object with this exact structure:
{{
    "business_recommendations": [
        {{
            "type": "category" or "location" or "sustainability_focus",
            "recommendation": "specific actionable recommendation",
            "reason": "explanation based on user's actual behavior"
        }}
    ],
    "sustainability_tips": [
        "specific actionable tips based on viewed business types"
    ],
    "suggested_categories": [
        "related categories based on actual view history"
    ]
}}

Key rules:
1. Use ONLY the provided interaction data
2. Make specific recommendations based on actual view counts
3. Reference actual categories and states from their history
4. Tie recommendations to their demonstrated interests
""")

def track_user_interaction(user_id: int, interaction_type: str, data: Dict) -> None:
    """
    Track user interactions for future recommendations.
    Types: view_business, search_location, filter_category
    """
    try:
        logger.info(f"\n[TRACKING] New interaction for user {user_id}")
        logger.info(f"Type: {interaction_type}")
        logger.info(f"Data: {json.dumps(data, cls=NumpyJSONEncoder, indent=2)}")

        db = next(get_db())

        # Convert numpy types to Python native types
        if 'business_id' in data:
            data['business_id'] = int(data['business_id'])
        if 'sustainability_score' in data and data['sustainability_score'] is not None:
            data['sustainability_score'] = float(data['sustainability_score'])

        interaction = UserInteraction(
            user_id=user_id,
            interaction_type=interaction_type,
            business_id=data.get('business_id'),
            category=data.get('category'),
            state=data.get('state'),
            sustainability_score=data.get('sustainability_score'),
            created_at=datetime.utcnow()
        )
        db.add(interaction)
        db.commit()
        logger.info("[SUCCESS] Saved interaction to database")
    except Exception as e:
        logger.error(f"[ERROR] Failed to track interaction: {str(e)}")
        if 'db' in locals():
            db.rollback()
    finally:
        if 'db' in locals():
            db.close()

def get_user_interaction_history(user_id: int) -> Dict:
    """
    Retrieve user's interaction history to generate recommendations
    """
    try:
        logger.info(f"\n[HISTORY] Fetching interaction history for user {user_id}")
        db = next(get_db())

        # Get interactions from the last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        interactions = (
            db.query(UserInteraction)
            .filter(
                UserInteraction.user_id == user_id,
                UserInteraction.created_at >= thirty_days_ago
            )
            .order_by(desc(UserInteraction.created_at))
            .all()
        )

        logger.info(f"[INFO] Found {len(interactions)} interactions")

        if not interactions:
            logger.info("[INFO] No interaction history found")
            return {
                "interaction_history": "New user, no interaction history yet",
                "categories_viewed": [],
                "states_searched": [],
                "avg_sustainability_score": 0,
                "category_counts": {}
            }

        # Process interactions with category frequency
        category_counts = {}
        states = []
        sustainability_scores = []
        interaction_descriptions = []

        for interaction in interactions:
            if interaction.category:
                category_counts[interaction.category] = category_counts.get(interaction.category, 0) + 1
            if interaction.state:
                states.append(interaction.state)
            if interaction.sustainability_score is not None:
                sustainability_scores.append(interaction.sustainability_score)

            # Create meaningful interaction description
            description = None
            if interaction.interaction_type == "view_business":
                description = f"Viewed {interaction.category} business"
            elif interaction.interaction_type == "search_location":
                description = f"Searched businesses in {interaction.state}"
            elif interaction.interaction_type == "filter_category":
                description = f"Explored {interaction.category} category"

            if description:
                interaction_descriptions.append(description)

        history = {
            "interaction_history": " • ".join(interaction_descriptions[-5:]),  # Last 5 interactions
            "categories_viewed": list(category_counts.keys()),
            "states_searched": list(set(states)),
            "avg_sustainability_score": sum(sustainability_scores) / len(sustainability_scores) if sustainability_scores else 0,
            "category_counts": category_counts
        }

        logger.info(f"[INFO] Processed history: {json.dumps(history, indent=2)}")
        return history

    except Exception as e:
        logger.error(f"[ERROR] Failed to get interaction history: {str(e)}")
        return {
            "interaction_history": "Error retrieving interaction history",
            "categories_viewed": [],
            "states_searched": [],
            "avg_sustainability_score": 0,
            "category_counts": {}
        }
    finally:
        if 'db' in locals():
            db.close()

def generate_recommendations(user_id: int, api_key: str) -> Dict:
    """
    Generate personalized recommendations using LangChain
    """
    try:
        logger.info(f"\n[GENERATING] Starting recommendation generation for user {user_id}")

        # Get user history
        user_history = get_user_interaction_history(user_id)
        logger.info(f"[INFO] User history retrieved: {json.dumps(user_history, indent=2)}")

        if not user_history["categories_viewed"]:
            logger.info("[INFO] No history found, returning default recommendations")
            return {
                "business_recommendations": [
                    {
                        "type": "getting_started",
                        "recommendation": "Start exploring sustainable businesses in your area",
                        "reason": "Welcome! Let's discover sustainable businesses together"
                    }
                ],
                "sustainability_tips": [
                    "Begin by exploring businesses with high sustainability scores",
                    "Look for certified sustainable businesses in your region"
                ],
                "suggested_categories": ["Retail", "Manufacturing", "Services"]
            }

        # Sort categories by view count for better recommendations
        sorted_categories = sorted(user_history["category_counts"].items(), key=lambda x: x[1], reverse=True)
        most_viewed_categories = [f"{cat} ({count} views)" for cat, count in sorted_categories[:3]]

        # Initialize OpenAI LLM with user's API key
        llm = ChatOpenAI(
            model_name="gpt-4o",
            temperature=0.7,
            api_key=api_key,
            response_format={ "type": "json_object" }  # Ensure JSON response
        )

        # Create chain for recommendation generation
        chain = recommendation_prompt | llm

        # Generate recommendations
        logger.info("[INFO] Sending request to OpenAI")
        result = chain.invoke({
            "interaction_history": user_history["interaction_history"],
            "most_viewed_categories": ", ".join(most_viewed_categories),
            "category_counts": json.dumps(user_history["category_counts"], indent=2),
            "states_searched": ", ".join(user_history["states_searched"]) or "None yet",
            "avg_sustainability_score": user_history["avg_sustainability_score"]
        })

        if result and hasattr(result, 'content'):
            result = result.content

        logger.info(f"[INFO] Raw LLM response: {result}")

        # Parse the result
        try:
            if isinstance(result, str):
                recommendations = json.loads(result)
            else:
                recommendations = result

            logger.info(f"[SUCCESS] Generated recommendations: {json.dumps(recommendations, indent=2)}")
            return recommendations

        except json.JSONDecodeError as e:
            logger.error(f"[ERROR] Failed to parse recommendations: {e}")
            logger.info(f"Raw response: {result}")
            return {
                "business_recommendations": [],
                "sustainability_tips": ["Focus on businesses with high sustainability scores"],
                "suggested_categories": []
            }

    except Exception as e:
        logger.error(f"[ERROR] Failed to generate recommendations: {str(e)}")
        return {
            "business_recommendations": [],
            "sustainability_tips": ["Focus on businesses with high sustainability scores"],
            "suggested_categories": []
        }

def format_recommendations_for_display(recommendations: Dict) -> Dict:
    """
    Format recommendations for Streamlit display
    """
    try:
        logger.info(f"[INFO] Formatting recommendations for display: {json.dumps(recommendations, indent=2)}")
        return {
            "business_recommendations": recommendations.get("business_recommendations", []),
            "sustainability_tips": recommendations.get("sustainability_tips", []),
            "suggested_categories": recommendations.get("suggested_categories", [])
        }
    except Exception as e:
        logger.error(f"[ERROR] Failed to format recommendations: {str(e)}")
        return {
            "business_recommendations": [],
            "sustainability_tips": [],
            "suggested_categories": []
        }