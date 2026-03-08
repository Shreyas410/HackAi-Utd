from pymongo import MongoClient
from pymongo.server_api import ServerApi
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime, timezone
import uuid
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 1. DEFINE THE SCHEMA (Application Level)
# ==========================================

# class ContentInteraction(BaseModel):
#     content_id: str
#     content_type: str # e.g., "video", "article"
#     timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
#     time_spent_seconds: int = 0
#     completion_rate_percentage: float = 0.0
#     sentiment_score: Optional[float] = None # From your custom engine

# class QuizAttempt(BaseModel):
#     quiz_id: str
#     topic: str
#     score_percentage: float
#     struggle_area_tags: List[str] = []
#     timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserSignup(BaseModel):
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    password_hash: str  # Remember to hash this before saving!

class UserSkillProfile(BaseModel):
    user_id: str  # Foreign key linking back to UserSignup
    
    # questionnaire component
    skill_to_learn: str
    starting_skill_level: int = Field(ge=1, le=10)  # 1 to 10 scale
    current_skill_level: int = Field(ge=1, le=10)
    
class UserProfile(BaseModel):
    user_id: str
    name: Optional[str] = None
    education: List[str] = []
    work_experience: List[str] = []
    skills: List[str] = []
    certifications: List[str] = []
    publications: List[str] = []
    resume_text: Optional[str] = None

# ==========================================
# 2. CONNECT TO MONGODB
# ==========================================

# Replace <password> with your actual database user password
MONGO_URI = os.getenv("MONGO_URI")

# Initialize the client
client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
db = client['hackai_db'] # This creates the database if it doesn't exist
users_collection = db['users']           # Collection for sign-up (email/password)
skills_collection = db['skills_profiles'] # Collection for questionnaire component (skills info)
profiles_collection = db['user_profiles'] # Collection for user profile data
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_user(email: str, password: str) -> tuple[bool, str]:
    """
    Creates a new user. Returns (success_bool, message).
    """
    # Check if user already exists
    if users_collection.find_one({"email": email}):
        return False, "User with this email already exists."

    hashed_pw = hash_password(password)
    new_user = UserSignup(
        email=email,
        password_hash=hashed_pw
    )

    try:
        users_collection.insert_one(new_user.model_dump())
        return True, "User created successfully."
    except Exception as e:
        return False, f"Database error: {e}"

def verify_user(email: str, password: str) -> tuple[bool, str]:
    """
    Verifies user credentials. Returns (success_bool, user_id_or_err_msg).
    """
    user_dict = users_collection.find_one({"email": email})
    if not user_dict:
        return False, "Invalid email or password."

    if not verify_password(password, user_dict.get("password_hash")):
        return False, "Invalid email or password."
    
    return True, user_dict.get("user_id")

def save_user_profile(user_id: str, profile_data: dict) -> tuple[bool, str]:
    """
    Saves or updates a user profile. Returns (success_bool, message).
    """
    try:
        profile_data['user_id'] = user_id
        # Use upsert to create if it doesn't exist, or update if it does
        profiles_collection.update_one(
            {"user_id": user_id},
            {"$set": profile_data},
            upsert=True
        )
        return True, "Profile saved successfully."
    except Exception as e:
        return False, f"Database error saving profile: {e}"

def get_user_profile(user_id: str) -> Optional[dict]:
    """
    Retrieves a user profile by user_id. Returns dictionary or None.
    """
    try:
        profile = profiles_collection.find_one({"user_id": user_id}, {"_id": 0})
        return profile
    except Exception as e:
        print(f"Database error fetching profile: {e}")
        return None

if __name__ == "__main__":
    # Ping the database to confirm connection
    try:
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(f"Connection failed: {e}")