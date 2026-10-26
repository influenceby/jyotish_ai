import requests
from app.config import ASTROLOGY_API_KEY
import traceback
import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from fastapi import Depends, Header

from app.database import Base, engine, get_db
from app.models import User, ChatMessage, Conversation, AstrologyCache
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    decode_token_payload
)

from app.services.gemini_service import gemini_service
from app.tools.astrology_tools import astrology_tools, BirthDetails


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

Base.metadata.create_all(bind=engine)


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="Jyotish AI",
    description="AI-powered Vedic life guidance",
    version="1.0.0",
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


# ============================================================
# STATIC FILES
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)



# ============================================================
# ADMIN LOGIN PAGE
# ============================================================

@app.get("/admin")
async def admin_login_page():
    return FileResponse(
        STATIC_DIR / "admin-login.html"
    )


# ============================================================
# REQUEST MODEL
# ============================================================

class ChatRequest(BaseModel):
    name: str
    gender: str
    date_of_birth: str
    time_of_birth: str
    hour: int
    minute: int
    place_of_birth: str
    question: str
    conversation_id: Optional[int] = None



# ============================================================
# AUTH MODELS
# ============================================================

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


# ============================================================
# REGISTER
# ============================================================

@app.post("/register")
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):

    email = request.email.lower().strip()

    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email is already registered."
        )

    user = User(
        name=request.name.strip(),
        email=email,
        password_hash=hash_password(
            request.password
        )
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(
        user.id
    )

    return {
        "status": "success",
        "message": "Registration successful",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "has_birth_details": False
        }
    }


# ============================================================
# LOGIN
# ============================================================

@app.post("/login")
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):

    email = request.email.lower().strip()

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    if not verify_password(
        request.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    token = create_access_token(
        user.id
    )

    has_birth_details = bool(
        user.date_of_birth
        and user.hour is not None
        and user.minute is not None
        and user.place_of_birth
    )

    return {
        "status": "success",
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "gender": user.gender,
            "date_of_birth": user.date_of_birth,
            "hour": user.hour,
            "minute": user.minute,
            "place_of_birth": user.place_of_birth,
            "has_birth_details": has_birth_details
        }
    }



# ============================================================
# AUTHENTICATED USER HELPER
# ============================================================

def get_authenticated_user(
    authorization: Optional[str],
    db: Session
):

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    try:
        scheme, token = authorization.split(" ", 1)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header."
        )

    if scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization scheme."
        )

    payload = decode_token_payload(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token."
        )

    if payload.get("role") == "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin token cannot access user endpoints."
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token."
        )

    user = db.query(User).filter(
        User.id == int(user_id)
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found."
        )

    return user




# ============================================================
# ADMIN MODELS
# ============================================================

class AdminLoginRequest(BaseModel):
    email: str
    password: str


# ============================================================
# ADMIN LOGIN
# ============================================================

@app.post("/admin/login")
async def admin_login(request: AdminLoginRequest):

    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_email or not admin_password:
        raise HTTPException(
            status_code=500,
            detail="Admin credentials are not configured."
        )

    if request.email.strip().lower() != admin_email.strip().lower():
        raise HTTPException(
            status_code=401,
            detail="Invalid admin credentials."
        )

    if request.password != admin_password:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin credentials."
        )

    token = create_access_token(
        user_id=0,
        role="admin"
    )

    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "role": "admin"
    }


# ============================================================
# ADMIN AUTH HELPER
# ============================================================

def require_admin(authorization: Optional[str]):

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Admin authentication required."
        )

    try:
        scheme, token = authorization.split(" ", 1)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header."
        )

    if scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization scheme."
        )

    payload = decode_token_payload(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired admin token."
        )

    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required."
        )

    return payload


# ============================================================
# ADMIN - LIST USERS
# ============================================================

@app.get("/admin/users")
async def admin_list_users(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):

    require_admin(authorization)

    users = db.query(User).order_by(
        User.created_at.desc()
    ).all()

    return {
        "status": "success",
        "total_users": len(users),
        "users": [
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "gender": user.gender,
                "date_of_birth": user.date_of_birth,
                "place_of_birth": user.place_of_birth,
                "has_astrology_data": bool(user.astrology_data),
                "created_at": (
                    user.created_at.isoformat()
                    if user.created_at else None
                )
            }
            for user in users
        ]
    }


# ============================================================
# ADMIN - LIST ALL MESSAGES
# ============================================================

@app.get("/admin/messages")
async def admin_list_messages(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):

    require_admin(authorization)

    results = db.query(
        ChatMessage,
        User.name,
        User.email
    ).join(
        User,
        ChatMessage.user_id == User.id
    ).order_by(
        ChatMessage.created_at.desc()
    ).all()

    return {
        "status": "success",
        "total_messages": len(results),
        "messages": [
            {
                "id": message.id,
                "user_id": message.user_id,
                "name": name,
                "email": email,
                "user_message": message.user_message,
                "ai_response": message.ai_response,
                "created_at": (
                    message.created_at.isoformat()
                    if message.created_at else None
                )
            }
            for message, name, email in results
        ]
    }



# ============================================================
# ADMIN - GET USER MESSAGES
# ============================================================

@app.get("/admin/users/{user_id}/messages")
async def admin_get_user_messages(
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):

    require_admin(authorization)

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100."
        )

    if offset < 0:
        raise HTTPException(
            status_code=400,
            detail="Offset cannot be negative."
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    total_messages = db.query(ChatMessage).filter(
        ChatMessage.user_id == user_id
    ).count()

    messages = db.query(ChatMessage).filter(
        ChatMessage.user_id == user_id
    ).order_by(
        ChatMessage.created_at.desc()
    ).offset(
        offset
    ).limit(
        limit
    ).all()

    return {
        "status": "success",

        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "gender": user.gender,
            "date_of_birth": user.date_of_birth,
            "place_of_birth": user.place_of_birth,
            "has_astrology_data": bool(user.astrology_data)
        },

        "total_messages": total_messages,
        "limit": limit,
        "offset": offset,

        "messages": [
            {
                "id": message.id,
                "user_message": message.user_message,
                "ai_response": message.ai_response,
                "created_at": (
                    message.created_at.isoformat()
                    if message.created_at else None
                )
            }
            for message in messages
        ]
    }


# ============================================================
# GET CURRENT USER
# ============================================================

@app.get("/me")
async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    try:
        scheme, token = authorization.split(" ", 1)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header."
        )

    if scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization scheme."
        )

    user_id = decode_access_token(token)

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token."
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found."
        )

    return {
        "status": "success",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "has_birth_details": bool(
                user.astrology_data
            )
        }
    }




# ============================================================
# HOME PAGE
# ============================================================

@app.get("/")
async def home():
    return FileResponse(
        STATIC_DIR / "index.html"
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health_check():

    return {
        "status": "success",
        "message": "Jyotish AI is running"
    }


# ============================================================
# GET LOCATION DETAILS
# ============================================================

async def get_location_details(place: str):

    """
    Convert place name into:

    - Latitude
    - Longitude

    Example:

    Bhubaneswar, India
        ↓
    Latitude: 20.2961
    Longitude: 85.8245
    """

    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": place,
        "format": "json",
        "limit": 1,
    }

    headers = {
        "User-Agent": "JyotishAI/1.0"
    }

    try:

        async with httpx.AsyncClient(
            timeout=15
        ) as client:

            response = await client.get(
                url,
                params=params,
                headers=headers,
            )

            response.raise_for_status()

            data = response.json()

        if not data:

            raise HTTPException(
                status_code=400,
                detail=(
                    "We couldn't find that place. "
                    "Please enter the city and country clearly."
                )
            )

        location = data[0]

        latitude = float(
            location["lat"]
        )

        longitude = float(
            location["lon"]
        )

        return {
            "latitude": latitude,
            "longitude": longitude,
        }

    except HTTPException:
        raise

    except Exception as error:

        print(
            "Location Error:",
            str(error)
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to find the location details right now."
            )
        )


# ============================================================
# TIMEZONE
# ============================================================

def get_timezone_offset() -> float:

    """
    DEMO VERSION

    Currently defaults to India timezone.

    Since your initial users/client are using India,
    this is okay for testing.

    Later we can make this dynamic for worldwide users.
    """

    return 5.5


# ============================================================
# DATE CONVERTER
# ============================================================

def parse_birth_date(date_string: str):

    """
    Expected frontend format:

    YYYY-MM-DD

    Example:

    1966-04-28
    """

    try:

        date_object = datetime.strptime(
            date_string,
            "%Y-%m-%d"
        )

        return {
            "day": date_object.day,
            "month": date_object.month,
            "year": date_object.year,
        }

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Invalid date of birth."
        )



# ============================================================
# GENERATE BIRTH CHART BEFORE ENTERING CHAT
# ============================================================

class BirthChartRequest(BaseModel):
    name: str
    gender: str
    date_of_birth: str
    hour: int
    minute: int
    place_of_birth: str


@app.post("/generate-chart")
async def generate_chart(
    request: BirthChartRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):

    try:

        # ----------------------------------------------------
        # GET LOGGED-IN USER
        # ----------------------------------------------------

        user = get_authenticated_user(
            authorization,
            db
        )

        print("\n" + "=" * 60)
        print("GENERATING BIRTH CHART")
        print("User:", user.email)
        print("=" * 60)

        # ----------------------------------------------------
        # PARSE DATE
        # ----------------------------------------------------

        date_details = parse_birth_date(
            request.date_of_birth
        )

        # ----------------------------------------------------
        # GET LOCATION
        # ----------------------------------------------------

        location = await get_location_details(
            request.place_of_birth
        )

        timezone = get_timezone_offset()

        # ----------------------------------------------------
        # BUILD BIRTH DETAILS
        # ----------------------------------------------------

        birth_details = BirthDetails(
            day=date_details["day"],
            month=date_details["month"],
            year=date_details["year"],
            hour=request.hour,
            minute=request.minute,
            latitude=location["latitude"],
            longitude=location["longitude"],
            timezone=timezone,
        )

        # ----------------------------------------------------
        # ASTROLOGY CACHE - CHECK BEFORE CALLING API
        # ----------------------------------------------------

        cache_key = (
            f"{birth_details.day}|"
            f"{birth_details.month}|"
            f"{birth_details.year}|"
            f"{birth_details.hour}|"
            f"{birth_details.minute}|"
            f"{birth_details.latitude:.6f}|"
            f"{birth_details.longitude:.6f}|"
            f"{birth_details.timezone:.2f}"
        )

        print("🔑 Astrology cache key:", cache_key)

        cached_chart = (
            db.query(AstrologyCache)
            .filter(AstrologyCache.cache_key == cache_key)
            .first()
        )

        if cached_chart:
            # ------------------------------------------------
            # CACHE HIT
            # ------------------------------------------------
            print("✅ ASTROLOGY CACHE HIT")
            print("🚫 AstrologyAPI call skipped")

            try:
                cached_data = json.loads(cached_chart.astro_data)

                if isinstance(cached_data, dict) and "astro_data" in cached_data:
                    astro_data = cached_data["astro_data"]
                    dasha_data = cached_data.get("dasha_data", {})
                else:
                    # Backward compatibility for old cache records
                    astro_data = cached_data
                    print("📡 Old cache format detected. Fetching Dasha...")
                    dasha_data = astrology_tools.get_current_dasha(
                        birth_details
                    )

                    cached_chart.astro_data = json.dumps(
                        {
                            "astro_data": astro_data,
                            "dasha_data": dasha_data
                        },
                        default=str
                    )
                    db.commit()

                print("📊 Dasha data available:", bool(dasha_data))

            except Exception as error:
                print("⚠️ Cached astrology data is invalid:", repr(error))
                print("🔄 Regenerating AstrologyAPI data...")

                astro_data = astrology_tools.get_astro_details(
                    birth_details
                )

                print("📡 Calling AstrologyAPI for Dasha...")
                dasha_data = astrology_tools.get_current_dasha(
                    birth_details
                )

                cached_chart.astro_data = json.dumps(
                    {
                        "astro_data": astro_data,
                        "dasha_data": dasha_data
                    },
                    default=str
                )
                db.commit()

        else:
            # ------------------------------------------------
            # CACHE MISS
            # ------------------------------------------------
            print("❌ ASTROLOGY CACHE MISS")
            print("📡 Calling AstrologyAPI...")

            astro_data = astrology_tools.get_astro_details(
                birth_details
            )

            print("📡 Calling AstrologyAPI for Dasha...")
            dasha_data = astrology_tools.get_current_dasha(
                birth_details
            )

            cache_data = {
                "astro_data": astro_data,
                "dasha_data": dasha_data
            }

            # Save AstrologyAPI chart + Dasha result to cache
            new_cache = AstrologyCache(
                cache_key=cache_key,
                day=birth_details.day,
                month=birth_details.month,
                year=birth_details.year,
                hour=birth_details.hour,
                minute=birth_details.minute,
                latitude=str(birth_details.latitude),
                longitude=str(birth_details.longitude),
                timezone=str(birth_details.timezone),
                astro_data=json.dumps(
                    cache_data,
                    default=str
                )
            )

            db.add(new_cache)
            db.commit()

            print("💾 AstrologyAPI result saved to cache")

        print("Birth chart data ready")

        # ----------------------------------------------------
        # SAVE USER BIRTH DETAILS
        # ----------------------------------------------------

        user.gender = request.gender
        user.date_of_birth = request.date_of_birth
        user.hour = request.hour
        user.minute = request.minute
        user.place_of_birth = request.place_of_birth

        # Save COMPLETE astrology JSON

        user.astrology_data = json.dumps(
            {
                "birth_details": birth_details.model_dump(),
                "astro_data": astro_data,
                "dasha_data": dasha_data
            }
        )

        db.commit()
        db.refresh(user)

        print("✅ Astrology data saved to database")

        # ----------------------------------------------------
        # RETURN SUCCESS
        # ----------------------------------------------------

        return {
            "status": "success",
            "message": "Birth chart generated and saved successfully"
        }

    except HTTPException:
        raise

    except Exception as error:

        print("\n❌ BIRTH CHART ERROR")
        print(type(error).__name__)
        print(str(error))
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Unable to generate your birth chart. Please try again."
        )



# ============================================================
# CONVERSATION HISTORY API
# ============================================================

@app.get("/conversations")
async def get_conversations(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    try:

        user = get_authenticated_user(
            authorization,
            db
        )

        conversations = (
            db.query(Conversation)
            .filter(
                Conversation.user_id == user.id
            )
            .order_by(
                Conversation.updated_at.desc(),
                Conversation.id.desc()
            )
            .all()
        )

        result = []

        for conversation in conversations:

            first_message = (
                db.query(ChatMessage)
                .filter(
                    ChatMessage.conversation_id == conversation.id,
                    ChatMessage.user_id == user.id
                )
                .order_by(
                    ChatMessage.created_at.asc(),
                    ChatMessage.id.asc()
                )
                .first()
            )

            last_message = (
                db.query(ChatMessage)
                .filter(
                    ChatMessage.conversation_id == conversation.id,
                    ChatMessage.user_id == user.id
                )
                .order_by(
                    ChatMessage.created_at.desc(),
                    ChatMessage.id.desc()
                )
                .first()
            )

            title = conversation.title

            if first_message:
                title = first_message.user_message.strip()

                if len(title) > 60:
                    title = title[:60].rstrip() + "..."

            result.append({
                "id": conversation.id,
                "title": title,
                "created_at": conversation.created_at.isoformat()
                    if conversation.created_at else None,
                "updated_at": conversation.updated_at.isoformat()
                    if conversation.updated_at else None,
                "message_count": (
                    db.query(ChatMessage)
                    .filter(
                        ChatMessage.conversation_id == conversation.id,
                        ChatMessage.user_id == user.id
                    )
                    .count()
                ),
                "last_message": (
                    last_message.user_message
                    if last_message else None
                )
            })

        return {
            "status": "success",
            "conversations": result
        }

    except HTTPException:
        raise

    except Exception as error:

        print("❌ CONVERSATION LIST ERROR:", repr(error))
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Unable to load your chat history."
        )


@app.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    try:

        user = get_authenticated_user(
            authorization,
            db
        )

        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id
            )
            .first()
        )

        if not conversation:

            raise HTTPException(
                status_code=404,
                detail="Conversation not found."
            )

        messages = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.conversation_id == conversation.id,
                ChatMessage.user_id == user.id
            )
            .order_by(
                ChatMessage.created_at.asc(),
                ChatMessage.id.asc()
            )
            .all()
        )

        return {
            "status": "success",
            "conversation": {
                "id": conversation.id,
                "title": conversation.title,
                "created_at": (
                    conversation.created_at.isoformat()
                    if conversation.created_at else None
                ),
                "updated_at": (
                    conversation.updated_at.isoformat()
                    if conversation.updated_at else None
                )
            },
            "messages": [
                {
                    "id": message.id,
                    "user_message": message.user_message,
                    "ai_response": message.ai_response,
                    "created_at": (
                        message.created_at.isoformat()
                        if message.created_at else None
                    )
                }
                for message in messages
            ]
        }

    except HTTPException:
        raise

    except Exception as error:

        print("❌ CONVERSATION LOAD ERROR:", repr(error))
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Unable to load this conversation."
        )


# ============================================================
# CHAT API
# ============================================================

@app.post("/chat")
async def chat(
    request: ChatRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    conversation = None
    chat_message = None

    try:
        user = get_authenticated_user(authorization, db)

        print("\n" + "=" * 60)
        print("NEW CHAT REQUEST")
        print("User:", user.email)
        print("=" * 60)

        if not request.question or not request.question.strip():
            raise HTTPException(
                status_code=400,
                detail="Please enter a question."
            )

        if not user.astrology_data:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Your astrology data has not been generated yet. "
                    "Please generate your birth chart first."
                )
            )

        try:
            astrology_data = json.loads(user.astrology_data)
            print("📦 Saved astrology data loaded successfully")
        except Exception as error:
            print("❌ Failed to load saved astrology data:", repr(error))
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail="Your saved astrology data could not be loaded. Please come back later."
            )

        # ----------------------------------------------------
        # GET / CREATE CONVERSATION
        # ----------------------------------------------------

        if request.conversation_id is not None:
            conversation = (
                db.query(Conversation)
                .filter(
                    Conversation.id == request.conversation_id,
                    Conversation.user_id == user.id
                )
                .first()
            )

            if not conversation:
                raise HTTPException(
                    status_code=404,
                    detail="Conversation not found."
                )

        else:
            conversation = Conversation(
                user_id=user.id,
                title=request.question.strip()[:255]
            )

            db.add(conversation)
            db.flush()

            print("🆕 New conversation created:", conversation.id)

        # Persist conversation BEFORE calling Gemini.
        db.commit()
        db.refresh(conversation)

        # ----------------------------------------------------
        # PERSIST USER MESSAGE BEFORE GEMINI
        # ----------------------------------------------------

        chat_message = ChatMessage(
            user_id=user.id,
            conversation_id=conversation.id,
            user_message=request.question.strip(),
            ai_response="[PROCESSING]"
        )

        db.add(chat_message)
        db.commit()
        db.refresh(chat_message)

        print("💾 User message persisted:", chat_message.id)

        # ----------------------------------------------------
        # GEMINI
        # ----------------------------------------------------

        print("\n🤖 Asking Raj Rao...")

        try:
            answer, new_interaction_id = await asyncio.to_thread(
                gemini_service.ask_question,
                name=user.name,
                gender=user.gender,
                astrology_data=astrology_data,
                question=request.question.strip(),
                previous_interaction_id=conversation.gemini_interaction_id,
            )

        except Exception as error:
            print("\n❌ GEMINI REQUEST FAILED")
            print("Error type:", type(error).__name__)
            print("Error:", str(error))
            traceback.print_exc()

            db.rollback()

            failed_message = (
                "I'm sorry, I couldn't prepare your guidance right now. "
                "Your question has been saved. Please try again."
            )

            chat_message = (
                db.query(ChatMessage)
                .filter(
                    ChatMessage.id == chat_message.id,
                    ChatMessage.user_id == user.id,
                    ChatMessage.conversation_id == conversation.id
                )
                .first()
            )

            if chat_message:
                chat_message.ai_response = failed_message
                conversation.updated_at = func.now()
                db.commit()

            raise HTTPException(
                status_code=503,
                detail=failed_message
            )

        # ----------------------------------------------------
        # VALIDATE GEMINI RESPONSE
        # ----------------------------------------------------

        if not answer or not answer.strip():
            print("❌ Gemini returned an empty response")

            failed_message = (
                "I'm sorry, I couldn't prepare a complete response right now. "
                "Your question has been saved. Please try again."
            )

            db.rollback()

            chat_message = (
                db.query(ChatMessage)
                .filter(
                    ChatMessage.id == chat_message.id,
                    ChatMessage.user_id == user.id,
                    ChatMessage.conversation_id == conversation.id
                )
                .first()
            )

            if chat_message:
                chat_message.ai_response = failed_message
                conversation.updated_at = func.now()
                db.commit()

            raise HTTPException(
                status_code=503,
                detail=failed_message
            )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        chat_message = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.id == chat_message.id,
                ChatMessage.user_id == user.id,
                ChatMessage.conversation_id == conversation.id
            )
            .first()
        )

        if not chat_message:
            raise RuntimeError(
                "Persisted chat message could not be reloaded."
            )

        chat_message.ai_response = answer.strip()

        conversation.gemini_interaction_id = (
            new_interaction_id or conversation.gemini_interaction_id
        )

        conversation.updated_at = func.now()

        db.commit()
        db.refresh(chat_message)

        print("\n✅ Response Generated")
        print("✅ Chat history saved successfully")
        print("Conversation ID:", conversation.id)
        print("Chat Message ID:", chat_message.id)

        return {
            "status": "success",
            "message": answer.strip(),
            "conversation_id": conversation.id,
            "chat_message_id": chat_message.id,
            "user": {
                "name": request.name,
                "place": request.place_of_birth,
            }
        }

    except HTTPException:
        raise

    except Exception as error:
        print("\n❌ CHAT ERROR")
        print("Error type:", type(error).__name__)
        print("Error:", str(error))
        traceback.print_exc()

        try:
            db.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail=(
                "I'm sorry, something went wrong while preparing "
                "your guidance. Please try again."
            )
        )


# ============================================================
# RUN LOCALLY
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

# ============================================================
# DOWNLOAD COMPLETE BIRTH CHART PDF
# ============================================================



@app.get("/download-chart-pdf")
async def download_chart_pdf(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Generate the official AstrologyAPI Mini Horoscope PDF
    for the currently authenticated user.
    """

    from fastapi.responses import Response

    # --------------------------------------------------------
    # 1. Authenticate CURRENT user
    # --------------------------------------------------------

    user = get_authenticated_user(authorization, db)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    # --------------------------------------------------------
    # 2. Check saved birth chart
    # --------------------------------------------------------

    if not user.astrology_data:
        raise HTTPException(
            status_code=400,
            detail="Please generate your birth chart first."
        )

    try:
        saved_data = json.loads(user.astrology_data)
        saved_birth = saved_data.get("birth_details", {})
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Saved birth chart data could not be read."
        )

    # --------------------------------------------------------
    # 3. Get THIS user's saved birth details
    # --------------------------------------------------------

    try:
        day = int(saved_birth["day"])
        month = int(saved_birth["month"])
        year = int(saved_birth["year"])
        hour = int(saved_birth["hour"])
        minute = int(saved_birth["minute"])

        latitude = float(saved_birth["latitude"])
        longitude = float(saved_birth["longitude"])
        timezone = float(saved_birth["timezone"])

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid saved birth details: {exc}"
        )

    # --------------------------------------------------------
    # 4. User information
    # --------------------------------------------------------

    name = user.name or "User"
    gender = (user.gender or "male").strip().lower()
    place = user.place_of_birth or "Unknown"

    if gender not in ["male", "female"]:
        gender = "male"

    # --------------------------------------------------------
    # 5. Official AstrologyAPI Mini Horoscope PDF payload
    # --------------------------------------------------------

    payload = {
        "name": name,
        "gender": gender,

        "day": day,
        "month": month,
        "year": year,
        "hour": hour,
        "min": minute,

        "lat": latitude,
        "lon": longitude,
        "language": "en",
        "tzone": timezone,

        "place": place,

        "chart_style": "NORTH_INDIAN",

        # Jyotish AI branding
        "footer_link": "https://www.jyotish.ai",
        "logo_url": "https://app.jyotish.ai/static/jyotish-logo.jpeg",
        "company_name": "Jyotish AI",
        "company_info": "Authentic Jyotish Knowledge, Education and Consultation",
        "domain_url": "https://www.jyotish.ai",
        "company_email": "raj@jyotish.ai",
        "company_landline": "",
        "company_mobile": "+919967079090"
    }

    # --------------------------------------------------------
    # 6. Official AstrologyAPI PDF endpoint
    #    Access Token authentication
    # --------------------------------------------------------

    pdf_api_url = (
        "https://pdf.astrologyapi.com/v1/mini_horoscope_pdf"
    )

    headers = {
        "x-astrologyapi-key": ASTROLOGY_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            pdf_api_url,
            headers=headers,
            json=payload,
            timeout=60
        )

    except requests.exceptions.RequestException as exc:
        print("AstrologyAPI PDF request error:", exc)

        raise HTTPException(
            status_code=502,
            detail="Unable to connect to AstrologyAPI PDF service."
        )

    # --------------------------------------------------------
    # 7. Check AstrologyAPI response
    # --------------------------------------------------------

    if not response.ok:
        print(
            "AstrologyAPI PDF HTTP error:",
            response.status_code,
            response.text
        )

        raise HTTPException(
            status_code=502,
            detail="AstrologyAPI could not generate the PDF."
        )

    try:
        pdf_result = response.json()
    except Exception:
        print("Invalid AstrologyAPI PDF response:", response.text)

        raise HTTPException(
            status_code=502,
            detail="Invalid response received from AstrologyAPI."
        )

    print("AstrologyAPI PDF response:", pdf_result)

    if not pdf_result.get("status"):
        raise HTTPException(
            status_code=502,
            detail="AstrologyAPI PDF generation failed."
        )

    pdf_url = pdf_result.get("pdf_url")

    if not pdf_url:
        raise HTTPException(
            status_code=502,
            detail="AstrologyAPI did not return a PDF URL."
        )

    # --------------------------------------------------------
    # 8. Download generated PDF
    # --------------------------------------------------------

    try:
        pdf_response = requests.get(
            pdf_url,
            timeout=60
        )

    except requests.exceptions.RequestException as exc:
        print("PDF download error:", exc)

        raise HTTPException(
            status_code=502,
            detail="Unable to download the generated PDF."
        )

    if not pdf_response.ok:
        print(
            "PDF download HTTP error:",
            pdf_response.status_code
        )

        raise HTTPException(
            status_code=502,
            detail="Generated PDF could not be downloaded."
        )

    pdf_bytes = pdf_response.content

    if not pdf_bytes:
        raise HTTPException(
            status_code=502,
            detail="Generated PDF is empty."
        )

    # --------------------------------------------------------
    # 9. Return PDF to the authenticated user
    # --------------------------------------------------------

    safe_name = "".join(
        c for c in name
        if c.isalnum() or c in (" ", "_", "-")
    ).strip()

    filename = (
        f"{safe_name or 'birth_chart'}_mini_horoscope.pdf"
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        }
    )
