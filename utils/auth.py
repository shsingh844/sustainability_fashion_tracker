import hashlib
import secrets
from datetime import datetime
from typing import Optional, Dict

import streamlit as st
from models.database import User, get_db

def hash_password(password: str) -> str:
    """Hash a password for storing."""
    salt = secrets.token_hex(8)
    pwdhash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('ascii'),
        100000
    )
    return f"{salt}${pwdhash.hex()}"

def verify_password(stored_password: str, provided_password: str) -> bool:
    """Verify a stored password against one provided by user"""
    salt = stored_password.split('$')[0]
    stored_pwdhash = stored_password.split('$')[1]
    pwdhash = hashlib.pbkdf2_hmac(
        'sha256',
        provided_password.encode('utf-8'),
        salt.encode('ascii'),
        100000
    )
    return pwdhash.hex() == stored_pwdhash

def init_session_state():
    """Initialize session state variables for authentication."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'last_recommendation_time' not in st.session_state:
        st.session_state.last_recommendation_time = None

def login_user(email: str, password: str) -> bool:
    """Authenticate a user and create a session."""
    try:
        db = next(get_db())
        user = db.query(User).filter(User.email == email).first()

        if user and verify_password(user.hashed_password, password):
            # Update last login
            user.last_login = datetime.utcnow()
            db.commit()

            # Set session state
            st.session_state.authenticated = True
            st.session_state.user = {
                'id': user.id,
                'email': user.email,
                'username': user.username
            }
            st.session_state.last_recommendation_time = None
            return True
        return False
    except Exception as e:
        st.error(f"Login error: {str(e)}")
        return False
    finally:
        if 'db' in locals():
            db.close()

def register_user(email: str, username: str, password: str) -> bool:
    """Register a new user."""
    try:
        db = next(get_db())

        # Check if user already exists
        if db.query(User).filter(User.email == email).first():
            st.error("Email already registered")
            return False

        if db.query(User).filter(User.username == username).first():
            st.error("Username already taken")
            return False

        # Create new user
        user = User(
            email=email,
            username=username,
            hashed_password=hash_password(password),
            created_at=datetime.utcnow()
        )

        db.add(user)
        db.commit()
        return True
    except Exception as e:
        st.error(f"Registration error: {str(e)}")
        return False
    finally:
        if 'db' in locals():
            db.close()

def logout_user():
    """Clear the session state and log out the user."""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.last_recommendation_time = None

def get_current_user() -> Optional[Dict]:
    """Get the current logged-in user's information."""
    if not st.session_state.get('authenticated', False):
        return None
    return st.session_state.user