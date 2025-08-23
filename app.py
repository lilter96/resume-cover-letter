#!/usr/bin/env python3
"""
Resume Generator Web Application - Redesigned
 
A modern web application for generating tailored resumes and cover letters
using AI. Features user accounts, credits system, and URL-based vacancy parsing.

Author: Generated for ML project
Date: 2025-08-22
"""

import os
import json
import time
import secrets
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

import aiofiles
from fastapi import FastAPI, HTTPException, Request, Depends, Cookie, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
import PyPDF2
import io
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Import our modules
from models import create_tables, get_db, User, Generation, PaymentOrder, CryptoWallet, PricingPlan, StripePaymentOrder
from auth import AuthManager, UserManager
from scripts.resume_generator import HumanLikeGenerator
from scripts.hh import HeadHunterAPI
from crypto_payment import CryptoPaymentService
from stripe_payment import StripePaymentService
from google_oauth import get_google_oauth_service
from metrics import metrics_collector, track_llm_usage, track_generation_metrics, track_payment_metrics, track_credit_metrics
from middleware import setup_middleware

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Resume Generator",
    description="AI-powered resume and cover letter generator with user accounts",
    version="2.0.0"
)

# Setup directories
STATIC_DIR = Path("static")
TEMPLATES_DIR = Path("templates")
GENERATED_DIR = Path("generated")

for directory in [STATIC_DIR, TEMPLATES_DIR, GENERATED_DIR]:
    directory.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Setup templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Initialize services
auth_manager = AuthManager(secret_key=os.getenv('SECRET_KEY', 'your-secret-key-here'))
user_manager = UserManager(auth_manager)
crypto_service = CryptoPaymentService()
stripe_service = None
google_oauth_service = None
generator = None

# Pydantic models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None
    location: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    name: str
    phone: Optional[str] = None
    location: Optional[str] = None
    experience_years: Optional[str] = None
    current_position: Optional[str] = None
    key_skills: List[str] = []
    education: Optional[str] = None
    achievements: Optional[str] = None
    github: Optional[str] = None

class VacancyURL(BaseModel):
    url: str

class GenerationSettings(BaseModel):
    temperature: float = 0.5
    length: str = "standard"
    tone: str = "professional"
    focus: str = "skills"
    format_style: str = "traditional"
    industry_adaptation: str = "auto"
    keyword_density: str = "moderate"
    personalization: str = "standard"
    special_instructions: str = ""

class DocumentGeneration(BaseModel):
    vacancy_url: str
    vacancy_data: Dict
    generation_settings: Optional[GenerationSettings] = None

# Setup middleware for metrics collection (must be done before startup)
setup_middleware(app)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global generator, stripe_service, google_oauth_service
    
    try:
        # Create database tables
        create_tables()
        
        # Initialize document generator
        generator = HumanLikeGenerator()
        
        # Initialize Stripe service (only if keys are provided)
        try:
            stripe_service = StripePaymentService()
            print("✅ Stripe payment service initialized")
        except ValueError as e:
            print(f"⚠️ Stripe service not initialized: {e}")
            print("💡 Set STRIPE_SECRET_KEY to enable Stripe payments")
        
        # Initialize Google OAuth service (only if keys are provided)
        try:
            google_oauth_service = get_google_oauth_service()
            if google_oauth_service:
                print("✅ Google OAuth service initialized")
            else:
                print("⚠️ Google OAuth service not initialized")
                print("💡 Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to enable Google login")
        except Exception as e:
            print(f"⚠️ Google OAuth service error: {e}")
            print("💡 Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to enable Google login")
        
        # Initialize metrics collection
        print("📊 Initializing metrics collection...")
        
        print("✅ All services initialized successfully")
        print("🚀 Resume Generator v2.0 is ready!")
        print("📊 Features: User accounts, Credits system, URL-based parsing, Dual payment options, Google OAuth, Production monitoring")
        print("📈 Metrics endpoint: /metrics")
        
    except Exception as e:
        print(f"❌ Error initializing services: {e}")

def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Get current authenticated user from token."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    return user_manager.get_user_by_token(db, token)

def require_auth(request: Request, db: Session = Depends(get_db)) -> User:
    """Require authentication - raise exception if not authenticated."""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    """Home page."""
    user = get_current_user(request, db)
    return templates.TemplateResponse("home.html", {
        "request": request,
        "user": user_manager.user_to_dict(user) if user else None
    })

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration page."""
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/api/register")
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register new user."""
    result = user_manager.register_user(
        db, user_data.email, user_data.password, user_data.name,
        user_data.phone, user_data.location
    )
    
    if result["success"]:
        response = JSONResponse(result)
        response.set_cookie("access_token", result["token"], httponly=True, max_age=60*60*24*7)
        return response
    
    return JSONResponse(result, status_code=400)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/api/login")
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login user."""
    result = user_manager.login_user(db, user_data.email, user_data.password)
    
    if result["success"]:
        response = JSONResponse(result)
        response.set_cookie("access_token", result["token"], httponly=True, max_age=60*60*24*7)
        return response
    
    return JSONResponse(result, status_code=400)

@app.post("/api/logout")
async def logout():
    """Logout user."""
    response = JSONResponse({"success": True, "message": "Logged out successfully"})
    response.delete_cookie("access_token")
    return response

# Google OAuth endpoints
@app.get("/auth/google")
async def google_login():
    """Initiate Google OAuth login."""
    if not google_oauth_service:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    authorization_url = google_oauth_service.get_authorization_url(state)
    
    response = JSONResponse({
        "success": True,
        "authorization_url": authorization_url,
        "state": state
    })
    
    # Store state in cookie for verification
    response.set_cookie("oauth_state", state, httponly=True, max_age=600)  # 10 minutes
    
    return response

@app.get("/auth/google/callback")
async def google_callback(request: Request, code: str = None, state: str = None, error: str = None, db: Session = Depends(get_db)):
    """Handle Google OAuth callback."""
    print(f"🔍 OAuth callback received - code: {code is not None}, state: {state}, error: {error}")
    
    if not google_oauth_service:
        print("❌ Google OAuth service not configured")
        raise HTTPException(status_code=503, detail="Google OAuth not configured")
    
    # Check for OAuth errors
    if error:
        print(f"❌ OAuth error: {error}")
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    
    if not code:
        print("❌ No authorization code provided")
        raise HTTPException(status_code=400, detail="Authorization code not provided")
    
    print(f"✅ Starting OAuth flow with code: {code[:20]}...")
    
    try:
        # Exchange code for user info
        print("🔄 Exchanging code for user info...")
        auth_result = await google_oauth_service.authenticate_user(code)
        
        if not auth_result:
            print("❌ Failed to authenticate with Google")
            raise HTTPException(status_code=400, detail="Failed to authenticate with Google")
        
        print("✅ Successfully authenticated with Google")
        print(f"📋 User info: {auth_result['user_info'].get('email', 'No email')}")
        
        # Extract user data
        user_data = google_oauth_service.extract_user_data(auth_result['user_info'])
        print(f"📋 Extracted user data: {user_data}")
        
        # Register or login user
        print("🔄 Registering/logging in user...")
        result = user_manager.register_or_login_google_user(db, user_data)
        
        if result["success"]:
            print("✅ User authentication successful")
            # Create response with redirect to dashboard
            response = HTMLResponse(f"""
            <html>
                <head>
                    <title>Login Successful</title>
                    <script>
                        // Redirect to dashboard
                        window.location.href = "/dashboard";
                    </script>
                </head>
                <body>
                    <p>Login successful! Redirecting...</p>
                </body>
            </html>
            """)
            
            # Set the access token cookie on server side
            response.set_cookie(
                "access_token",
                result['token'],
                httponly=True,
                max_age=60*60*24*7,  # 7 days
                path="/"
            )
            
            # Clear OAuth state cookie
            response.delete_cookie("oauth_state")
            
            return response
        else:
            print(f"❌ User authentication failed: {result['message']}")
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in OAuth callback: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@app.get("/api/auth/google/status")
async def google_auth_status():
    """Check if Google OAuth is available."""
    return JSONResponse({
        "available": google_oauth_service is not None,
        "configured": google_oauth_service.is_configured() if google_oauth_service else False
    })

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """User dashboard."""
    # Get recent generations
    recent_generations = db.query(Generation).filter(
        Generation.user_id == user.id
    ).order_by(Generation.created_at.desc()).limit(5).all()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user_manager.user_to_dict(user),
        "recent_generations": recent_generations
    })

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user: User = Depends(require_auth)):
    """User profile page."""
    return templates.TemplateResponse("profile_new.html", {
        "request": request,
        "user": user_manager.user_to_dict(user)
    })

@app.post("/api/profile")
async def update_profile(profile_data: UserProfile, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Update user profile."""
    result = user_manager.update_user_profile(db, user.id, profile_data.dict())
    return JSONResponse(result)

@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...), language: str = Form("auto"), user: User = Depends(require_auth)):
    """Upload and parse PDF resume to auto-fill profile."""
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            return JSONResponse({
                "success": False,
                "message": "Only PDF files are supported"
            }, status_code=400)
        
        # Read PDF content
        content = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        
        # Extract text from all pages
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        if not text.strip():
            return JSONResponse({
                "success": False,
                "message": "Could not extract text from PDF. Please ensure it's not a scanned document."
            }, status_code=400)
        
        # Determine language to use for parsing
        if language == "auto":
            # Auto-detect language based on Cyrillic characters
            cyrillic_count = sum(1 for char in text if '\u0400' <= char <= '\u04FF')
            total_chars = len([char for char in text if char.isalpha()])
            if total_chars > 0 and cyrillic_count / total_chars > 0.1:
                detected_lang = "ru"
            else:
                detected_lang = "en"
        else:
            # Use user-selected language
            detected_lang = language
        
        # Use LLM to extract structured information from resume
        if generator:
            try:
                # Create language-specific prompts
                if detected_lang == "ru":
                    prompt = f"""
Проанализируй этот текст резюме и извлеки структурированную информацию для автозаполнения профиля.

ТЕКСТ РЕЗЮМЕ:
{text[:4000]}...

Извлеки и верни JSON с этими полями:
{{
    "name": "полное имя человека",
    "phone": "номер телефона если найден",
    "location": "город/местоположение если найдено",
    "current_position": "текущая должность или последняя позиция",
    "experience_years": "оцени годы опыта (0-1, 1-2, 2-3, 3-5, 5-7, 7-10, 10+)",
    "key_skills": ["навык1", "навык2", "навык3", "навык4", "навык5", "навык6", "навык7", "навык8"],
    "education": "высшее образование и учебное заведение",
    "achievements": "ключевые достижения и успехи краткое описание",
    "github": "ссылка на github профиль если найдена"
}}

Сосредоточься на извлечении:
- Личная контактная информация
- Профессиональный опыт и навыки (МАКСИМАЛЬНО ПОЛНЫЙ СПИСОК)
- Образование
- Заметные достижения
- Технические навыки и технологии (ВСЕ упомянутые)
- GitHub или портфолио ссылки

Для опыта работы:
- Если указан конкретный период работы, посчитай общий стаж
- Если есть даты начала и окончания работы, вычисли точное количество лет
- Если опыт менее года, выбери "0-1"
- Если 1-2 года, выбери "1-2" и так далее

Для навыков:
- Включи ВСЕ технические навыки
- Включи языки программирования
- Включи фреймворки и библиотеки
- Включи инструменты разработки
- Включи базы данных
- Включи методологии разработки
- Включи soft skills если упомянуты

Верни только JSON, никакого другого текста.
"""
                else:
                    prompt = f"""
Analyze this resume text and extract structured information for auto-filling a profile form.

RESUME TEXT:
{text[:4000]}...

Extract and return JSON with these fields:
{{
    "name": "full name of the person",
    "phone": "phone number if found",
    "location": "city/location if found",
    "current_position": "current job title or most recent position",
    "experience_years": "estimate years of experience (0-1, 1-2, 2-3, 3-5, 5-7, 7-10, 10+)",
    "key_skills": ["skill1", "skill2", "skill3", "skill4", "skill5", "skill6", "skill7", "skill8"],
    "education": "highest education degree and institution",
    "achievements": "key achievements and accomplishments summary",
    "github": "github profile URL if found"
}}

Focus on extracting:
- Personal contact information
- Professional experience and skills (COMPREHENSIVE LIST)
- Education background
- Notable achievements
- Technical skills and technologies (ALL mentioned)
- GitHub or portfolio links

For work experience:
- If specific work periods are mentioned, calculate total experience
- If there are start and end dates for jobs, compute exact years
- If experience is less than a year, choose "0-1"
- If 1-2 years, choose "1-2" and so on

For skills:
- Include ALL technical skills mentioned
- Include programming languages
- Include frameworks and libraries
- Include development tools
- Include databases
- Include development methodologies
- Include soft skills if mentioned

Only return the JSON, no other text.
"""
                
                system_message = "You are an expert at analyzing resumes and extracting structured data. Return only valid JSON with comprehensive skill extraction."
                if detected_lang == "ru":
                    system_message = "Ты эксперт по анализу резюме и извлечению структурированных данных. Верни только валидный JSON с максимально полным извлечением навыков."
                
                start_time = time.time()
                response = generator.client.chat.completions.create(
                    model=generator.model,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=2000
                )
                
                # Track LLM usage
                llm_time = time.time() - start_time
                tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 2000
                estimated_cost = tokens_used * 0.00001  # Rough estimate for Claude-3-Haiku
                track_llm_usage(generator.model, "resume_parsing", tokens_used, estimated_cost, llm_time, True)
                
                result = response.choices[0].message.content
                
                # Try to parse JSON
                try:
                    json_start = result.find('{')
                    json_end = result.rfind('}') + 1
                    if json_start != -1 and json_end != -1:
                        json_str = result[json_start:json_end]
                        parsed_data = json.loads(json_str)
                        
                        # Clean and validate extracted data
                        profile_data = {
                            "name": parsed_data.get("name", "").strip(),
                            "phone": parsed_data.get("phone", "").strip(),
                            "location": parsed_data.get("location", "").strip(),
                            "current_position": parsed_data.get("current_position", "").strip(),
                            "experience_years": parsed_data.get("experience_years", "").strip(),
                            "key_skills": [skill.strip() for skill in parsed_data.get("key_skills", []) if skill.strip()],
                            "education": parsed_data.get("education", "").strip(),
                            "achievements": parsed_data.get("achievements", "").strip(),
                            "github": parsed_data.get("github", "").strip()
                        }
                        
                        # Add metadata about parsing
                        skills_count = len(profile_data["key_skills"])
                        lang_msg = "Russian" if detected_lang == "ru" else "English"
                        user_choice = "Auto-detected" if language == "auto" else "User-selected"
                        
                        return JSONResponse({
                            "success": True,
                            "message": f"Resume parsed successfully ({user_choice} {lang_msg}, {skills_count} skills extracted)",
                            "data": profile_data,
                            "metadata": {
                                "user_language_choice": language,
                                "detected_language": detected_lang,
                                "skills_count": skills_count,
                                "text_length": len(text)
                            },
                            "raw_text": text[:1000] + "..." if len(text) > 1000 else text
                        })
                        
                except json.JSONDecodeError as e:
                    return JSONResponse({
                        "success": False,
                        "message": f"Error parsing extracted data: {str(e)}",
                        "raw_text": text[:1000] + "..." if len(text) > 1000 else text
                    }, status_code=500)
                    
            except Exception as e:
                return JSONResponse({
                    "success": False,
                    "message": f"Error processing resume with AI: {str(e)}",
                    "raw_text": text[:1000] + "..." if len(text) > 1000 else text
                }, status_code=500)
        
        # Fallback: return raw text if LLM processing fails
        return JSONResponse({
            "success": True,
            "message": "Resume uploaded successfully (manual extraction required)",
            "data": {},
            "raw_text": text[:1000] + "..." if len(text) > 1000 else text
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "message": f"Error processing PDF: {str(e)}"
        }, status_code=500)

@app.get("/generate", response_class=HTMLResponse)
async def generate_page(request: Request, user: User = Depends(require_auth)):
    """Document generation page."""
    return templates.TemplateResponse("generate.html", {
        "request": request,
        "user": user_manager.user_to_dict(user)
    })

@app.post("/api/parse-vacancy")
async def parse_vacancy(vacancy_data: VacancyURL, user: User = Depends(require_auth)):
    """Parse vacancy from HeadHunter URL."""
    try:
        url = vacancy_data.url.strip()
        
        # Validate HeadHunter URL format
        import re
        hh_pattern = r'https://hh\.ru/vacancy/(\d+)'
        match = re.match(hh_pattern, url)
        
        if not match:
            raise HTTPException(status_code=400, detail="Invalid HeadHunter URL format")
        
        vacancy_id = match.group(1)
        
        # Parse vacancy using HeadHunter API
        api = HeadHunterAPI()
        vacancy_json = api.get_vacancy_details(vacancy_id)
        
        if not vacancy_json:
            raise HTTPException(status_code=404, detail="Could not fetch vacancy data")
        
        # Extract basic information
        title = vacancy_json.get('name', '')
        company = vacancy_json.get('employer', {}).get('name', '')
        description = vacancy_json.get('description', '')
        
        # Extract salary information
        salary_info = vacancy_json.get('salary')
        salary = ""
        if salary_info:
            salary_from = salary_info.get('from')
            salary_to = salary_info.get('to')
            currency = salary_info.get('currency', 'RUB')
            
            if salary_from and salary_to:
                salary = f"{salary_from}-{salary_to} {currency}"
            elif salary_from:
                salary = f"от {salary_from} {currency}"
            elif salary_to:
                salary = f"до {salary_to} {currency}"
        
        # Use LLM to extract structured information
        vacancy_data = {
            "vacancy_title": title,
            "company": company,
            "url": url,
            "salary": salary,
            "technologies": "",
            "skills": "",
            "experience_level": "",
            "domain": ""
        }
        
        if generator:
            try:
                prompt = f"""
Analyze this HeadHunter vacancy and extract structured information:

VACANCY TITLE: {title}
COMPANY: {company}
DESCRIPTION: {description[:2000]}...

Extract and return JSON with these fields:
{{
    "technologies": "comma-separated list of technologies mentioned",
    "skills": "comma-separated list of skills mentioned", 
    "experience_level": "Junior/Middle/Senior based on requirements",
    "domain": "industry domain (e.g., E-commerce, Gaming, etc.)"
}}

Focus on extracting:
- Programming languages and technologies
- Required skills and competencies
- Experience level requirements
- Industry domain

Only return the JSON, no other text.
"""
                
                start_time = time.time()
                response = generator.client.chat.completions.create(
                    model=generator.model,
                    messages=[
                        {"role": "system", "content": "You are an expert at analyzing job vacancies and extracting structured data. Return only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=1000
                )
                
                # Track LLM usage
                llm_time = time.time() - start_time
                tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 1000
                estimated_cost = tokens_used * 0.00001  # Rough estimate for Claude-3-Haiku
                track_llm_usage(generator.model, "vacancy_parsing", tokens_used, estimated_cost, llm_time, True)
                
                result = response.choices[0].message.content
                
                # Try to parse JSON
                try:
                    json_start = result.find('{')
                    json_end = result.rfind('}') + 1
                    if json_start != -1 and json_end != -1:
                        json_str = result[json_start:json_end]
                        parsed_data = json.loads(json_str)
                        
                        # Update vacancy data with LLM results
                        vacancy_data.update({
                            "technologies": parsed_data.get("technologies", ""),
                            "skills": parsed_data.get("skills", ""),
                            "experience_level": parsed_data.get("experience_level", ""),
                            "domain": parsed_data.get("domain", "")
                        })
                        
                except json.JSONDecodeError:
                    pass
                    
            except Exception as e:
                print(f"LLM parsing error: {e}")
        
        return JSONResponse({
            "success": True,
            "message": "Vacancy parsed successfully",
            "vacancy": vacancy_data
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "message": f"Error parsing vacancy: {str(e)}"
        }, status_code=500)

def calculate_generation_cost(settings: Optional[GenerationSettings]) -> float:
    """Calculate the cost in credits based on generation settings."""
    if not settings:
        return 1.0
    
    base_cost = 1.0
    
    # Higher temperature costs more due to more processing
    if settings.temperature >= 0.7:
        base_cost += 0.5
    if settings.temperature >= 0.9:
        base_cost += 0.5
    
    # Longer documents cost more
    if settings.length == 'detailed':
        base_cost += 0.5
    elif settings.length == 'extensive':
        base_cost += 1.0
    
    # Higher personalization costs more
    if settings.personalization == 'high':
        base_cost += 0.5
    elif settings.personalization == 'ultra':
        base_cost += 1.0
    
    # Heavy keyword optimization costs more
    if settings.keyword_density == 'heavy':
        base_cost += 0.5
    
    return base_cost

@app.post("/api/generate-documents")
async def generate_documents(generation_data: DocumentGeneration,
                           user: User = Depends(require_auth),
                           db: Session = Depends(get_db)):
    """Generate resume and cover letter with advanced AI settings."""
    try:
        # Calculate cost based on settings
        settings = generation_data.generation_settings or GenerationSettings()
        credit_cost = calculate_generation_cost(settings)
        
        # Check if user has enough credits (admin users have unlimited)
        if not user.is_admin and user.credits < credit_cost:
            return JSONResponse({
                "success": False,
                "message": f"Insufficient credits. You need {credit_cost} credits but have {user.credits}. Please purchase more credits to continue."
            }, status_code=402)
        
        # Use credits
        credit_result = user_manager.use_credits(db, user.id, credit_cost, f"Document generation with {settings.length} length, {settings.personalization} personalization")
        if not credit_result["success"]:
            return JSONResponse(credit_result, status_code=402)
        
        # Prepare user profile
        user_profile = {
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "location": user.location,
            "experience_years": user.experience_years,
            "current_position": user.current_position,
            "key_skills": json.loads(user.key_skills) if user.key_skills else [],
            "education": user.education,
            "achievements": user.achievements,
            "github": user.github
        }
        
        # Generate documents with custom settings
        start_time = time.time()
        
        # Pass generation settings to the generator
        generation_options = {
            'temperature': settings.temperature,
            'length': settings.length,
            'tone': settings.tone,
            'focus': settings.focus,
            'format_style': settings.format_style,
            'industry_adaptation': settings.industry_adaptation,
            'keyword_density': settings.keyword_density,
            'personalization': settings.personalization,
            'special_instructions': settings.special_instructions
        }
        
        resume = generator.generate_document('resume', generation_data.vacancy_data, user_profile, generation_options)
        cover_letter = generator.generate_document('cover_letter', generation_data.vacancy_data, user_profile, generation_options)
        
        generation_time = time.time() - start_time
        
        # Track generation metrics
        user_type = "admin" if user.is_admin else "regular"
        track_generation_metrics(user_type, generation_time, True)
        
        # Track credit usage
        if not user.is_admin:
            track_credit_metrics("usage", 1, user_type)
        
        # Create organized folder structure
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        vacancy_title_clean = "".join(c for c in generation_data.vacancy_data.get('vacancy_title', 'vacancy') if c.isalnum() or c in (' ', '-', '_')).rstrip()
        company_clean = "".join(c for c in generation_data.vacancy_data.get('company', 'company') if c.isalnum() or c in (' ', '-', '_')).rstrip()
        
        folder_name = f"{user.id}_{company_clean}_{vacancy_title_clean}_{timestamp}"
        output_dir = GENERATED_DIR / folder_name
        output_dir.mkdir(exist_ok=True)
        
        # Save files
        resume_file = output_dir / "resume.txt"
        cover_file = output_dir / "cover_letter.txt"
        vacancy_file = output_dir / "vacancy_info.json"
        
        async with aiofiles.open(resume_file, 'w', encoding='utf-8') as f:
            await f.write(resume)
        
        async with aiofiles.open(cover_file, 'w', encoding='utf-8') as f:
            await f.write(cover_letter)
        
        # Clean vacancy info for JSON serialization
        def clean_value(value):
            if value is None or (hasattr(value, '__iter__') and not isinstance(value, str) and len(str(value)) == 0):
                return ""
            return str(value)
        
        vacancy_info = {
            "vacancy_title": clean_value(generation_data.vacancy_data.get('vacancy_title')),
            "company": clean_value(generation_data.vacancy_data.get('company')),
            "url": clean_value(generation_data.vacancy_data.get('url')),
            "salary": clean_value(generation_data.vacancy_data.get('salary')),
            "technologies": clean_value(generation_data.vacancy_data.get('technologies')),
            "skills": clean_value(generation_data.vacancy_data.get('skills')),
            "experience_level": clean_value(generation_data.vacancy_data.get('experience_level')),
            "domain": clean_value(generation_data.vacancy_data.get('domain')),
            "generated_at": datetime.now().isoformat()
        }
        
        async with aiofiles.open(vacancy_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(vacancy_info, indent=2, ensure_ascii=False))
        
        # Save generation record to database
        generation_record = Generation(
            user_id=user.id,
            vacancy_url=generation_data.vacancy_url,
            vacancy_title=generation_data.vacancy_data.get('vacancy_title'),
            company=generation_data.vacancy_data.get('company'),
            vacancy_data=json.dumps(generation_data.vacancy_data),
            resume_text=resume,
            cover_letter_text=cover_letter,
            generation_time=generation_time,
            folder_path=str(output_dir)
        )
        
        db.add(generation_record)
        db.commit()
        
        return JSONResponse({
            "success": True,
            "message": "Documents generated successfully",
            "data": {
                "resume_text": resume,
                "cover_letter_text": cover_letter,
                "vacancy_info": vacancy_info,
                "generated_at": timestamp,
                "folder": str(output_dir),
                "remaining_credits": credit_result["remaining_credits"]
            }
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "message": f"Error generating documents: {str(e)}"
        }, status_code=500)

@app.get("/results", response_class=HTMLResponse)
async def results_page(request: Request, folder: str, user: User = Depends(require_auth)):
    """Results page showing generated documents."""
    try:
        folder_path = Path(folder)
        if not folder_path.exists() or not str(folder_path).startswith(str(GENERATED_DIR)):
            raise HTTPException(status_code=404, detail="Generated documents not found")
        
        # Check if folder belongs to current user
        if not folder_path.name.startswith(user.id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Read generated files
        resume_file = folder_path / "resume.txt"
        cover_file = folder_path / "cover_letter.txt"
        vacancy_file = folder_path / "vacancy_info.json"
        
        if not all([resume_file.exists(), cover_file.exists(), vacancy_file.exists()]):
            raise HTTPException(status_code=404, detail="Some generated files are missing")
        
        # Read file contents
        async with aiofiles.open(resume_file, 'r', encoding='utf-8') as f:
            resume_text = await f.read()
        
        async with aiofiles.open(cover_file, 'r', encoding='utf-8') as f:
            cover_letter_text = await f.read()
        
        async with aiofiles.open(vacancy_file, 'r', encoding='utf-8') as f:
            vacancy_info_str = await f.read()
            vacancy_info = json.loads(vacancy_info_str)
        
        folder_name = folder_path.name
        
        return templates.TemplateResponse("results_new.html", {
            "request": request,
            "user": user_manager.user_to_dict(user),
            "resume_text": resume_text,
            "cover_letter_text": cover_letter_text,
            "vacancy_info": vacancy_info,
            "folder_name": folder_name
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading results: {str(e)}")

@app.get("/download/{folder_name}/{filename}")
async def download_file(folder_name: str, filename: str, user: User = Depends(require_auth)):
    """Download generated file."""
    # Check if folder belongs to current user
    if not folder_name.startswith(user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    file_path = GENERATED_DIR / folder_name / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

@app.get("/api/user")
async def get_user_info(user: User = Depends(require_auth)):
    """Get current user information."""
    return JSONResponse(user_manager.user_to_dict(user))

# Payment endpoints
@app.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request, user: User = Depends(require_auth)):
    """Pricing page for credit purchases."""
    return templates.TemplateResponse("pricing.html", {
        "request": request,
        "user": user_manager.user_to_dict(user)
    })

@app.get("/api/pricing-plans")
async def get_pricing_plans(db: Session = Depends(get_db)):
    """Get available pricing plans."""
    plans = crypto_service.get_pricing_plans(db)
    return JSONResponse({"success": True, "plans": plans})

@app.post("/api/create-payment-order")
async def create_payment_order(plan_data: dict, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Create a new payment order."""
    plan_id = plan_data.get("plan_id")
    if not plan_id:
        return JSONResponse({"success": False, "message": "Plan ID is required"}, status_code=400)
    
    result = crypto_service.create_payment_order(db, user.id, plan_id)
    return JSONResponse(result)

@app.get("/api/payment-status/{order_id}")
async def check_payment_status(order_id: str, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Check payment status for an order."""
    result = crypto_service.check_payment_status(db, order_id)
    return JSONResponse(result)

@app.get("/api/order-status/{order_id}")
async def get_order_status(order_id: str, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Get order status and details."""
    result = crypto_service.get_order_status(db, order_id)
    return JSONResponse(result)

@app.get("/payment/{order_id}", response_class=HTMLResponse)
async def payment_page(request: Request, order_id: str, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Payment page for a specific order."""
    order_result = crypto_service.get_order_status(db, order_id)
    
    if not order_result["success"]:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return templates.TemplateResponse("payment.html", {
        "request": request,
        "user": user_manager.user_to_dict(user),
        "order": order_result["order"]
    })

# Stripe Payment Endpoints
@app.get("/api/stripe/pricing-plans")
async def get_stripe_pricing_plans(db: Session = Depends(get_db)):
    """Get available pricing plans for Stripe payments."""
    if not stripe_service:
        return JSONResponse({"success": False, "message": "Stripe service not available"}, status_code=503)
    
    plans = stripe_service.get_pricing_plans(db)
    return JSONResponse({"success": True, "plans": plans})

@app.post("/api/stripe/create-payment-intent")
async def create_stripe_payment_intent(plan_data: dict, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Create a Stripe Payment Intent for credit purchase."""
    if not stripe_service:
        return JSONResponse({"success": False, "message": "Stripe service not available"}, status_code=503)
    
    plan_id = plan_data.get("plan_id")
    if not plan_id:
        return JSONResponse({"success": False, "message": "Plan ID is required"}, status_code=400)
    
    result = stripe_service.create_payment_intent(db, user.id, plan_id)
    return JSONResponse(result)

@app.get("/api/stripe/payment-status/{order_id}")
async def get_stripe_payment_status(order_id: str, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Get Stripe payment status for an order."""
    if not stripe_service:
        return JSONResponse({"success": False, "message": "Stripe service not available"}, status_code=503)
    
    result = stripe_service.get_payment_status(db, order_id)
    return JSONResponse(result)

@app.post("/api/stripe/cancel-payment/{order_id}")
async def cancel_stripe_payment(order_id: str, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Cancel a pending Stripe payment."""
    if not stripe_service:
        return JSONResponse({"success": False, "message": "Stripe service not available"}, status_code=503)
    
    result = stripe_service.cancel_payment(db, order_id, user.id)
    return JSONResponse(result)

@app.get("/api/stripe/payment-history")
async def get_stripe_payment_history(user: User = Depends(require_auth), db: Session = Depends(get_db), limit: int = 10):
    """Get user's Stripe payment history."""
    if not stripe_service:
        return JSONResponse({"success": False, "message": "Stripe service not available"}, status_code=503)
    
    result = stripe_service.get_user_payment_history(db, user.id, limit)
    return JSONResponse(result)

@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events."""
    if not stripe_service:
        return JSONResponse({"success": False, "message": "Stripe service not available"}, status_code=503)
    
    try:
        payload = await request.body()
        signature = request.headers.get("stripe-signature")
        
        if not signature:
            return JSONResponse({"success": False, "message": "Missing signature"}, status_code=400)
        
        result = stripe_service.handle_webhook(payload, signature, db)
        return JSONResponse(result)
        
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Webhook error: {str(e)}"}, status_code=400)

@app.get("/stripe-payment/{order_id}", response_class=HTMLResponse)
async def stripe_payment_page(request: Request, order_id: str, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Stripe payment page for a specific order."""
    if not stripe_service:
        raise HTTPException(status_code=503, detail="Stripe service not available")
    
    order_result = stripe_service.get_payment_status(db, order_id)
    
    if not order_result["success"]:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return templates.TemplateResponse("stripe_payment.html", {
        "request": request,
        "user": user_manager.user_to_dict(user),
        "order": order_result["order"],
        "stripe_publishable_key": stripe_service.stripe_publishable_key
    })

# Combined payment endpoints (both crypto and Stripe)
@app.get("/api/payment-methods")
async def get_available_payment_methods():
    """Get available payment methods."""
    methods = []
    
    # Crypto payments are always available
    methods.append({
        "id": "crypto",
        "name": "Cryptocurrency (USDT TRC20)",
        "description": "Pay with USDT on TRON network",
        "icon": "₮",
        "available": True
    })
    
    # Stripe payments (if configured)
    methods.append({
        "id": "stripe",
        "name": "Credit/Debit Card",
        "description": "Pay with Visa, Mastercard, or other cards",
        "icon": "💳",
        "available": stripe_service is not None
    })
    
    return JSONResponse({"success": True, "methods": methods})

# Metrics endpoints
@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/api/metrics/dashboard")
async def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Get metrics for internal dashboard."""
    try:
        snapshot = metrics_collector.collect_all_metrics(db)
        return JSONResponse({
            "success": True,
            "metrics": {
                "timestamp": snapshot.timestamp.isoformat(),
                "total_users": snapshot.total_users,
                "dau": snapshot.dau,
                "wau": snapshot.wau,
                "mau": snapshot.mau,
                "total_generations": snapshot.total_generations,
                "daily_generations": snapshot.daily_generations,
                "total_revenue": snapshot.total_revenue,
                "daily_revenue": snapshot.daily_revenue,
                "conversion_rate": snapshot.conversion_rate,
                "arpu": snapshot.arpu
            }
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "message": f"Error collecting metrics: {str(e)}"
        }, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)