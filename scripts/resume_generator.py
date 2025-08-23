#!/usr/bin/env python3
"""
Human-Like Resume and Cover Letter Generator

Generates professional, human-like resumes and cover letters tailored to specific 
vacancies from the parsed HeadHunter database. Uses advanced prompt engineering 
to create undetectable AI-generated content.

Author: Generated for ML project
Date: 2025-08-22
"""

import pandas as pd
import json
import re
import os
import sys
from typing import Dict, List, Optional
from datetime import datetime
import logging
from dotenv import load_dotenv
from openai import OpenAI
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import USER_PROFILE, LINKEDIN_CONFIG
try:
    from linkedin_parser import LinkedInParser
except ImportError:
    LinkedInParser = None

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LanguageDetector:
    """Detect language of vacancy text."""
    
    @staticmethod
    def detect_language(text: str) -> str:
        """
        Detect if text is primarily Russian or English.
        
        Args:
            text: Text to analyze
            
        Returns:
            'ru' for Russian, 'en' for English
        """
        if not text:
            return 'en'
        
        # Count Cyrillic characters
        cyrillic_count = len(re.findall(r'[а-яё]', text.lower()))
        latin_count = len(re.findall(r'[a-z]', text.lower()))
        
        total_letters = cyrillic_count + latin_count
        if total_letters == 0:
            return 'en'
        
        cyrillic_ratio = cyrillic_count / total_letters
        
        # If more than 30% Cyrillic, consider it Russian
        return 'ru' if cyrillic_ratio > 0.3 else 'en'


class HumanLikeGenerator:
    """Generate human-like, undetectable AI documents."""
    
    def __init__(self):
        """Initialize the generator with OpenRouter LLM."""
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable.")
        
        self.model = os.getenv('OPENROUTER_MODEL', 'anthropic/claude-3-sonnet')
        self.app_name = os.getenv('OPENROUTER_APP_NAME', 'Resume-Generator')
        self.app_url = os.getenv('OPENROUTER_APP_URL', 'https://github.com/user/resume-gen')
        
        # Initialize OpenAI client with OpenRouter endpoint
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
            default_headers={
                "HTTP-Referer": self.app_url,
                "X-Title": self.app_name,
            }
        )
        
        logger.info(f"Initialized Human-Like Generator with model: {self.model}")
    
    def _create_human_like_prompt(self, document_type: str, language: str,
                                 vacancy_data: Dict, user_profile: Dict, generation_options: Dict = None) -> str:
        """Create a prompt that generates human-like, undetectable content with advanced settings."""
        
        if generation_options is None:
            generation_options = {}
        
        if language == 'ru':
            return self._create_russian_prompt(document_type, vacancy_data, user_profile, generation_options)
        else:
            return self._create_english_prompt(document_type, vacancy_data, user_profile, generation_options)
    
    def _create_english_prompt(self, document_type: str, vacancy_data: Dict, user_profile: Dict, generation_options: Dict) -> str:
        """Create English prompt for human-like document generation with advanced settings."""
        
        # Extract generation settings
        length = generation_options.get('length', 'standard')
        tone = generation_options.get('tone', 'professional')
        focus = generation_options.get('focus', 'skills')
        format_style = generation_options.get('format_style', 'traditional')
        industry_adaptation = generation_options.get('industry_adaptation', 'auto')
        keyword_density = generation_options.get('keyword_density', 'moderate')
        personalization = generation_options.get('personalization', 'standard')
        special_instructions = generation_options.get('special_instructions', '')
        
        # Create length-specific instructions
        length_instructions = {
            'concise': "Keep the content concise and focused. Use bullet points and brief descriptions. Aim for essential information only.",
            'standard': "Use standard professional length. Include relevant details with good balance between brevity and completeness.",
            'detailed': "Provide comprehensive details. Include specific examples, metrics, and thorough descriptions of experiences and achievements.",
            'extensive': "Create an extensive, thorough document. Include comprehensive details, multiple examples, and in-depth descriptions of all relevant experiences."
        }
        
        # Create tone-specific instructions
        tone_instructions = {
            'professional': "Maintain a professional, polished tone throughout. Use formal language and industry-standard terminology.",
            'confident': "Write with confidence and assertiveness. Highlight achievements boldly and demonstrate strong self-assurance.",
            'friendly': "Use a warm, approachable tone that builds connection. Be personable while maintaining professionalism.",
            'dynamic': "Write with energy and enthusiasm. Use action-oriented language that demonstrates drive and initiative.",
            'academic': "Use scholarly, precise language. Focus on research, publications, and intellectual contributions."
        }
        
        # Create focus-specific instructions
        focus_instructions = {
            'skills': "Emphasize technical skills, competencies, and abilities. Highlight skill-based achievements and capabilities.",
            'experience': "Focus on work experience, career progression, and professional accomplishments. Emphasize tenure and growth.",
            'achievements': "Highlight specific accomplishments, awards, and measurable results. Use numbers and concrete outcomes.",
            'education': "Emphasize educational background, certifications, and academic achievements. Highlight learning and development.",
            'leadership': "Focus on leadership experience, team management, and strategic contributions. Emphasize influence and impact."
        }
        
        # Create industry adaptation instructions
        industry_instructions = ""
        if industry_adaptation != 'auto':
            industry_instructions = f"\nINDUSTRY ADAPTATION: Tailor the language, terminology, and examples specifically for the {industry_adaptation} industry. Use industry-specific jargon and highlight relevant experience."
        
        # Create keyword density instructions
        keyword_instructions = {
            'light': "Use job-relevant keywords naturally and sparingly. Focus on organic integration.",
            'moderate': "Include job-relevant keywords strategically throughout the document. Balance keyword usage with natural flow.",
            'heavy': "Optimize heavily for job-relevant keywords. Include multiple variations and synonyms while maintaining readability."
        }
        
        # Create personalization instructions
        personalization_instructions = {
            'minimal': "Keep personal touches minimal. Focus on professional facts and achievements.",
            'standard': "Include appropriate personal elements that show personality while maintaining professionalism.",
            'high': "Add significant personal touches, stories, and individual voice. Show unique personality and perspective."
        }
        
        base_instructions = f"""
You are writing as a real person applying for a job. Write naturally, with personality and genuine enthusiasm.
CRITICAL: This must be completely undetectable as AI-generated content. Use these techniques:

1. NATURAL WRITING STYLE:
   - Use contractions (I'm, don't, can't, I've)
   - Vary sentence lengths naturally
   - Include personal opinions and preferences
   - Use conversational tone where appropriate
   - Add subtle imperfections (not errors, just human-like flow)

2. PERSONAL TOUCH:
   - Show genuine excitement about the opportunity
   - Include specific examples with real numbers
   - Mention personal motivations and goals
   - Use "I" statements and personal experiences
   - Add unique perspectives on industry trends

3. AVOID AI PATTERNS:
   - Don't use overly formal or robotic language
   - Avoid perfect structure or templated phrases
   - Don't list things in perfect order
   - Include natural transitions and flow
   - Use industry slang and casual expressions

4. AUTHENTICITY MARKERS:
   - Show real understanding of the company/role
   - Demonstrate genuine interest (not generic enthusiasm)
   - Include personal career story elements
   - Use specific technical details naturally
   - Show personality and individual voice

GENERATION SETTINGS:
- LENGTH: {length_instructions[length]}
- TONE: {tone_instructions[tone]}
- FOCUS: {focus_instructions[focus]}
- KEYWORD OPTIMIZATION: {keyword_instructions[keyword_density]}
- PERSONALIZATION: {personalization_instructions[personalization]}
{industry_instructions}

{f"SPECIAL INSTRUCTIONS: {special_instructions}" if special_instructions else ""}
"""
        
        if document_type == 'resume':
            linkedin_info = ""
            if user_profile.get('linkedin_data'):
                linkedin_info = f"""
LINKEDIN PROFILE DATA (use this for enhanced details):
- Professional Summary: {user_profile['linkedin_data'].get('summary', 'N/A')}
- LinkedIn Experience: {json.dumps(user_profile.get('linkedin_experience', []), indent=2)}
- LinkedIn Education: {json.dumps(user_profile.get('linkedin_education', []), indent=2)}
- LinkedIn Skills: {user_profile.get('linkedin_skills', [])}
- LinkedIn Projects: {json.dumps(user_profile.get('linkedin_projects', []), indent=2)}
- LinkedIn Certifications: {user_profile.get('linkedin_certifications', [])}
"""
            
            return f"""{base_instructions}

TASK: Write a professional RESUME in standard resume format tailored for this specific job opportunity.

JOB DETAILS:
- Position: {vacancy_data.get('vacancy_title', 'N/A')}
- Company: {vacancy_data.get('company', 'N/A')}
- Required Technologies: {vacancy_data.get('technologies', 'N/A')}
- Key Skills: {vacancy_data.get('skills', 'N/A')}
- Experience Level: {vacancy_data.get('experience_level', 'N/A')}
- Domain: {vacancy_data.get('domain', 'N/A')}

USER PROFILE:
{json.dumps(user_profile, indent=2)}
{linkedin_info}

IMPORTANT: Write a RESUME, not a cover letter! Use standard resume structure:

1. CONTACT INFORMATION (name, phone, email, location, LinkedIn)
2. PROFESSIONAL SUMMARY (brief 2-3 sentence overview, use LinkedIn summary if available)
3. WORK EXPERIENCE (use LinkedIn experience data if available, job title, company, dates, achievements with numbers)
4. TECHNICAL SKILLS (categorized: programming languages, frameworks, tools - merge with LinkedIn skills)
5. EDUCATION (use LinkedIn education if available, institution, degree, year)
6. PROJECTS (use LinkedIn projects if available, name, description, technologies, results)
7. CERTIFICATIONS (include LinkedIn certifications if available)

If LinkedIn data is available, prioritize and enhance the resume with that information.
Write as a confident professional who knows their value. Be specific and results-oriented.
Tailor skills and experience to match the job requirements.
Use bullet points and clear sections. No excessive enthusiasm - just professional confidence.
"""
        
        else:  # cover letter
            return f"""{base_instructions}

TASK: Write a compelling cover letter for this specific job application.

JOB DETAILS:
- Position: {vacancy_data.get('vacancy_title', 'N/A')}
- Company: {vacancy_data.get('company', 'N/A')}
- Required Technologies: {vacancy_data.get('technologies', 'N/A')}
- Key Skills: {vacancy_data.get('skills', 'N/A')}
- Experience Level: {vacancy_data.get('experience_level', 'N/A')}
- Domain: {vacancy_data.get('domain', 'N/A')}

USER PROFILE:
{json.dumps(user_profile, indent=2)}

Write a cover letter that sounds like a real person wrote it. Include:
- Personal opening that shows genuine interest
- Specific reasons why you want THIS job at THIS company
- Relevant experience with concrete examples
- How you can contribute to their specific needs
- Natural, enthusiastic closing

Make it conversational but professional. Show real personality and authentic interest.
Avoid generic phrases - make it specific to this opportunity.
"""
    
    def _create_russian_prompt(self, document_type: str, vacancy_data: Dict, user_profile: Dict, generation_options: Dict) -> str:
        """Create Russian prompt for human-like document generation with advanced settings."""
        
        # Extract generation settings
        length = generation_options.get('length', 'standard')
        tone = generation_options.get('tone', 'professional')
        focus = generation_options.get('focus', 'skills')
        format_style = generation_options.get('format_style', 'traditional')
        industry_adaptation = generation_options.get('industry_adaptation', 'auto')
        keyword_density = generation_options.get('keyword_density', 'moderate')
        personalization = generation_options.get('personalization', 'standard')
        special_instructions = generation_options.get('special_instructions', '')
        
        # Create length-specific instructions in Russian
        length_instructions = {
            'concise': "Пиши кратко и по существу. Используй маркированные списки и краткие описания. Только самая важная информация.",
            'standard': "Используй стандартную профессиональную длину. Включай релевантные детали с хорошим балансом между краткостью и полнотой.",
            'detailed': "Предоставь подробную информацию. Включай конкретные примеры, метрики и детальные описания опыта и достижений.",
            'extensive': "Создай обширный, подробный документ. Включай исчерпывающие детали, множество примеров и глубокие описания всего релевантного опыта."
        }
        
        # Create tone-specific instructions in Russian
        tone_instructions = {
            'professional': "Поддерживай профессиональный, отточенный тон. Используй формальный язык и стандартную отраслевую терминологию.",
            'confident': "Пиши с уверенностью и напористостью. Выделяй достижения смело и демонстрируй сильную самоуверенность.",
            'friendly': "Используй теплый, располагающий тон, который создает связь. Будь приветливым, сохраняя профессионализм.",
            'dynamic': "Пиши с энергией и энтузиазмом. Используй ориентированный на действие язык, демонстрирующий драйв и инициативу.",
            'academic': "Используй научный, точный язык. Фокусируйся на исследованиях, публикациях и интеллектуальных достижениях."
        }
        
        # Create focus-specific instructions in Russian
        focus_instructions = {
            'skills': "Делай акцент на технических навыках, компетенциях и способностях. Выделяй достижения, основанные на навыках.",
            'experience': "Фокусируйся на опыте работы, карьерном росте и профессиональных достижениях. Подчеркивай стаж и развитие.",
            'achievements': "Выделяй конкретные достижения, награды и измеримые результаты. Используй цифры и конкретные результаты.",
            'education': "Делай акцент на образовательном фоне, сертификатах и академических достижениях. Подчеркивай обучение и развитие.",
            'leadership': "Фокусируйся на лидерском опыте, управлении командой и стратегических вкладах. Подчеркивай влияние и воздействие."
        }
        
        # Create industry adaptation instructions in Russian
        industry_instructions = ""
        if industry_adaptation != 'auto':
            industry_instructions = f"\nАДАПТАЦИЯ ПОД ОТРАСЛЬ: Адаптируй язык, терминологию и примеры специально для отрасли {industry_adaptation}. Используй отраслевой жаргон и выделяй релевантный опыт."
        
        # Create keyword density instructions in Russian
        keyword_instructions = {
            'light': "Используй релевантные ключевые слова естественно и умеренно. Фокусируйся на органичной интеграции.",
            'moderate': "Включай релевантные ключевые слова стратегически по всему документу. Балансируй использование ключевых слов с естественным потоком.",
            'heavy': "Оптимизируй активно под релевантные ключевые слова. Включай множественные вариации и синонимы, сохраняя читаемость."
        }
        
        # Create personalization instructions in Russian
        personalization_instructions = {
            'minimal': "Минимизируй личные штрихи. Фокусируйся на профессиональных фактах и достижениях.",
            'standard': "Включай подходящие личные элементы, которые показывают личность, сохраняя профессионализм.",
            'high': "Добавляй значительные личные штрихи, истории и индивидуальный голос. Показывай уникальную личность и перспективу."
        }
        
        base_instructions = f"""
Ты пишешь как реальный профессионал, подающий заявку на работу. Пиши сдержанно, профессионально, но с личностью.
КРИТИЧЕСКИ ВАЖНО: Это должно звучать как обычный человек, а не как восторженный робот. Используй эти принципы:

1. ЕСТЕСТВЕННЫЙ ПРОФЕССИОНАЛЬНЫЙ СТИЛЬ:
   - Пиши спокойно и уверенно, без излишних эмоций
   - Используй простые, понятные предложения
   - Избегай восклицательных знаков и чрезмерного энтузиазма
   - Будь конкретным и по делу
   - Используй профессиональную лексику, но не заумную

2. СДЕРЖАННЫЙ ЛИЧНЫЙ ПОДХОД:
   - Показывай заинтересованность, но не восторг
   - Приводи конкретные примеры и цифры
   - Говори о своих целях реалистично
   - Используй "я" естественно, без навязчивости
   - Демонстрируй понимание индустрии

3. ИЗБЕГАЙ ИСКУССТВЕННОСТИ:
   - НЕ используй фразы типа "я подпрыгнул от волнения"
   - НЕ пиши "это моя мечта" или "я в восторге"
   - НЕ используй слишком эмоциональные выражения
   - НЕ пиши как маркетолог или продавец
   - Избегай клише и шаблонных фраз

4. ПРИЗНАКИ НАСТОЯЩЕГО ЧЕЛОВЕКА:
   - Пиши как опытный специалист, который знает свою ценность
   - Показывай реальное понимание задач и требований
   - Говори о конкретном опыте без преувеличений
   - Используй технические термины естественно
   - Будь уверенным, но не высокомерным

НАСТРОЙКИ ГЕНЕРАЦИИ:
- ДЛИНА: {length_instructions[length]}
- ТОН: {tone_instructions[tone]}
- ФОКУС: {focus_instructions[focus]}
- ОПТИМИЗАЦИЯ КЛЮЧЕВЫХ СЛОВ: {keyword_instructions[keyword_density]}
- ПЕРСОНАЛИЗАЦИЯ: {personalization_instructions[personalization]}
{industry_instructions}

{f"СПЕЦИАЛЬНЫЕ ИНСТРУКЦИИ: {special_instructions}" if special_instructions else ""}
"""
        
        if document_type == 'resume':
            return f"""{base_instructions}

ЗАДАЧА: Напиши профессиональное РЕЗЮМЕ в стандартном формате резюме, адаптированное под эту конкретную вакансию.

ДЕТАЛИ ВАКАНСИИ:
- Позиция: {vacancy_data.get('vacancy_title', 'Не указано')}
- Компания: {vacancy_data.get('company', 'Не указано')}
- Требуемые технологии: {vacancy_data.get('technologies', 'Не указано')}
- Ключевые навыки: {vacancy_data.get('skills', 'Не указано')}
- Уровень опыта: {vacancy_data.get('experience_level', 'Не указано')}
- Сфера: {vacancy_data.get('domain', 'Не указано')}

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
{json.dumps(user_profile, indent=2)}

ВАЖНО: Напиши именно РЕЗЮМЕ, а не сопроводительное письмо! Используй стандартную структуру резюме:

1. КОНТАКТНАЯ ИНФОРМАЦИЯ (имя, телефон, email, локация)
2. ПРОФЕССИОНАЛЬНОЕ РЕЗЮМЕ (краткое описание 2-3 предложения)
3. ОПЫТ РАБОТЫ (должность, компания, период, достижения с цифрами)
4. ТЕХНИЧЕСКИЕ НАВЫКИ (по категориям: языки программирования, фреймворки, инструменты)
5. ОБРАЗОВАНИЕ (учебное заведение, степень, год)
6. ПРОЕКТЫ (название, описание, технологии, результаты)

Пиши как профессионал, который знает свою ценность. Без лишних эмоций, четко и по делу.
Адаптируй навыки и опыт под требования вакансии.
"""
        
        else:  # cover letter
            return f"""{base_instructions}

ЗАДАЧА: Напиши профессиональное сопроводительное письмо для этой заявки на работу.

ДЕТАЛИ ВАКАНСИИ:
- Позиция: {vacancy_data.get('vacancy_title', 'Не указано')}
- Компания: {vacancy_data.get('company', 'Не указано')}
- Требуемые технологии: {vacancy_data.get('technologies', 'Не указано')}
- Ключевые навыки: {vacancy_data.get('skills', 'Не указано')}
- Уровень опыта: {vacancy_data.get('experience_level', 'Не указано')}
- Сфера: {vacancy_data.get('domain', 'Не указано')}

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
{json.dumps(user_profile, indent=2)}

Напиши сопроводительное письмо, которое звучит как написанное обычным профессионалом. Включи:
- Спокойное, профессиональное обращение
- Краткое объяснение, почему эта позиция тебе интересна
- Конкретные примеры релевантного опыта с цифрами
- Как твои навыки подходят для решения их задач
- Сдержанное, но уверенное заключение

Пиши как уверенный в себе специалист, который знает свою ценность. Без восторгов и эмоций.
Будь конкретным и профессиональным. Избегай клише и шаблонных фраз.
"""
    
    def generate_document(self, document_type: str, vacancy_data: Dict,
                         user_profile: Dict, generation_options: Dict = None, language: str = None) -> str:
        """
        Generate a human-like document (resume or cover letter) with advanced settings.
        
        Args:
            document_type: 'resume' or 'cover_letter'
            vacancy_data: Parsed vacancy information
            user_profile: User's personal and professional information
            generation_options: Advanced generation settings (temperature, length, tone, etc.)
            language: 'ru' or 'en', auto-detected if None
            
        Returns:
            Generated document text
        """
        # Set default generation options
        if generation_options is None:
            generation_options = {}
        
        # Extract generation settings with defaults
        temperature = generation_options.get('temperature', 0.8)
        length = generation_options.get('length', 'standard')
        tone = generation_options.get('tone', 'professional')
        focus = generation_options.get('focus', 'skills')
        format_style = generation_options.get('format_style', 'traditional')
        industry_adaptation = generation_options.get('industry_adaptation', 'auto')
        keyword_density = generation_options.get('keyword_density', 'moderate')
        personalization = generation_options.get('personalization', 'standard')
        special_instructions = generation_options.get('special_instructions', '')
        if language is None:
            # Auto-detect language from vacancy title and description
            text_to_analyze = f"{vacancy_data.get('vacancy_title', '')} {vacancy_data.get('keywords', '')} {vacancy_data.get('skills', '')}"
            language = LanguageDetector.detect_language(text_to_analyze)
            
            # Additional check: if title contains Russian words, prefer Russian
            title = vacancy_data.get('vacancy_title', '')
            if any(word in title.lower() for word in ['команду', 'модели', 'поставок', 'специалист', 'разработчик', 'аналитик']):
                language = 'ru'
        
        logger.info(f"Generating {document_type} in {language} for {vacancy_data.get('vacancy_title', 'Unknown')} with settings: temp={temperature}, length={length}, tone={tone}")
        
        prompt = self._create_human_like_prompt(document_type, language, vacancy_data, user_profile, generation_options)
        
        # Calculate max tokens based on length setting
        max_tokens_map = {
            'concise': 1000,
            'standard': 2000,
            'detailed': 3000,
            'extensive': 4000
        }
        max_tokens = max_tokens_map.get(length, 2000)
        
        # Adjust system message based on tone
        system_messages = {
            'professional': "You are an expert at writing professional, human-like resumes and cover letters that are completely undetectable as AI-generated content. Your writing is natural, personal, and authentic.",
            'confident': "You are an expert at writing confident, assertive resumes and cover letters that showcase achievements boldly. Your writing is natural, personal, and demonstrates strong self-assurance.",
            'friendly': "You are an expert at writing approachable, personable resumes and cover letters that connect with readers. Your writing is natural, warm, and builds rapport.",
            'dynamic': "You are an expert at writing energetic, action-oriented resumes and cover letters that demonstrate drive and initiative. Your writing is natural, engaging, and shows momentum.",
            'academic': "You are an expert at writing scholarly, research-focused resumes and cover letters that emphasize intellectual contributions. Your writing is natural, precise, and academically rigorous."
        }
        system_message = system_messages.get(tone, system_messages['professional'])
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            result = response.choices[0].message.content
            logger.info(f"Successfully generated {document_type}")
            return result
            
        except Exception as e:
            logger.error(f"Document generation failed: {e}")
            return f"Error generating {document_type}: {str(e)}"


class VacancySelector:
    """Select and load vacancies from the parsed database."""
    
    def __init__(self, csv_file: str = 'hh_vacancies.csv'):
        """Initialize with vacancy database file."""
        self.csv_file = csv_file
        self.vacancies = None
        self.load_vacancies()
    
    def load_vacancies(self):
        """Load vacancies from CSV file."""
        try:
            self.vacancies = pd.read_csv(self.csv_file)
            logger.info(f"Loaded {len(self.vacancies)} vacancies from {self.csv_file}")
        except FileNotFoundError:
            logger.error(f"Vacancy file {self.csv_file} not found. Run the parser first.")
            self.vacancies = pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading vacancies: {e}")
            self.vacancies = pd.DataFrame()
    
    def search_vacancies(self, query: str = None, company: str = None, 
                        experience_level: str = None) -> pd.DataFrame:
        """
        Search vacancies by various criteria.
        
        Args:
            query: Search in vacancy title
            company: Filter by company name
            experience_level: Filter by experience level
            
        Returns:
            Filtered DataFrame
        """
        if self.vacancies.empty:
            return pd.DataFrame()
        
        result = self.vacancies.copy()
        
        if query:
            mask = result['vacancy_title'].str.contains(query, case=False, na=False)
            result = result[mask]
        
        if company:
            mask = result['company'].str.contains(company, case=False, na=False)
            result = result[mask]
        
        if experience_level:
            mask = result['experience_level'].str.contains(experience_level, case=False, na=False)
            result = result[mask]
        
        return result
    
    def get_vacancy_by_index(self, index: int) -> Dict:
        """Get vacancy data by DataFrame index."""
        if self.vacancies.empty or index >= len(self.vacancies):
            return {}
        
        return self.vacancies.iloc[index].to_dict()
    
    def display_vacancies(self, df: pd.DataFrame, limit: int = 10):
        """Display vacancies in a readable format."""
        if df.empty:
            print("No vacancies found.")
            return
        
        print(f"\nFound {len(df)} vacancies:")
        print("=" * 80)
        
        for i, (idx, row) in enumerate(df.head(limit).iterrows()):
            print(f"{i+1}. [{idx}] {row['vacancy_title']}")
            print(f"   Company: {row['company']}")
            print(f"   Experience: {row['experience_level']} | Domain: {row['domain']}")
            print(f"   Salary: {row['salary']}")
            print(f"   Technologies: {row['technologies'][:100]}...")
            print("-" * 80)
        
        if len(df) > limit:
            print(f"... and {len(df) - limit} more vacancies")


def main():
    """Main function for interactive resume/cover letter generation."""
    print("🎯 Human-Like Resume & Cover Letter Generator")
    print("=" * 50)
    
    # Initialize components
    try:
        generator = HumanLikeGenerator()
        selector = VacancySelector()
        
        # Initialize LinkedIn parser if enabled
        linkedin_parser = None
        if LINKEDIN_CONFIG['enabled'] and LinkedInParser:
            try:
                linkedin_parser = LinkedInParser()
                print("📱 LinkedIn parser initialized")
            except Exception as e:
                print(f"⚠️  LinkedIn parser failed to initialize: {e}")
                linkedin_parser = None
        
    except Exception as e:
        print(f"Error initializing: {e}")
        return
    
    if selector.vacancies.empty:
        print("No vacancies found. Please run the HeadHunter parser first.")
        return
    
    # Interactive vacancy selection
    print(f"\nLoaded {len(selector.vacancies)} vacancies from database.")
    
    while True:
        print("\nOptions:")
        print("1. Search vacancies")
        print("2. Browse all vacancies")
        print("3. Generate documents for specific vacancy")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            query = input("Search query (vacancy title): ").strip()
            company = input("Company name (optional): ").strip() or None
            level = input("Experience level (optional): ").strip() or None
            
            results = selector.search_vacancies(query, company, level)
            selector.display_vacancies(results)
        
        elif choice == '2':
            selector.display_vacancies(selector.vacancies, limit=20)
        
        elif choice == '3':
            try:
                index = int(input("Enter vacancy index: "))
                vacancy = selector.get_vacancy_by_index(index)
                
                if not vacancy:
                    print("Invalid vacancy index.")
                    continue
                
                print(f"\nSelected: {vacancy['vacancy_title']} at {vacancy['company']}")
                print(f"Vacancy URL: {vacancy.get('url', 'N/A')}")
                
                # Use user profile from config and enhance with LinkedIn if available
                user_profile = USER_PROFILE.copy()
                
                # Enhance with LinkedIn data if parser is available
                if linkedin_parser and user_profile.get('linkedin'):
                    print("🔄 Enhancing profile with LinkedIn data...")
                    try:
                        user_profile = linkedin_parser.enhance_user_profile(user_profile)
                        print("✅ Profile enhanced with LinkedIn data")
                    except Exception as e:
                        print(f"⚠️  LinkedIn enhancement failed: {e}")
                
                # Allow user to override some fields if needed
                print(f"\nUsing profile: {user_profile['name']}")
                if user_profile.get('linkedin_data'):
                    print(f"📱 LinkedIn: {user_profile.get('linkedin', 'N/A')}")
                    print(f"💼 Enhanced with: {len(user_profile.get('linkedin_experience', []))} experiences, {len(user_profile.get('linkedin_skills', []))} skills")
                
                override = input("Override any fields? (y/n): ").strip().lower()
                if override == 'y':
                    user_profile["name"] = input(f"Full name [{user_profile['name']}]: ") or user_profile["name"]
                    user_profile["experience_years"] = input(f"Years of experience [{user_profile['experience_years']}]: ") or user_profile["experience_years"]
                    user_profile["current_position"] = input(f"Current position [{user_profile['current_position']}]: ") or user_profile["current_position"]
                
                # Generate documents
                print("\nGenerating documents...")
                
                resume = generator.generate_document('resume', vacancy, user_profile)
                cover_letter = generator.generate_document('cover_letter', vacancy, user_profile)
                
                # Create organized folder structure
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Clean vacancy title for folder name
                vacancy_title_clean = re.sub(r'[^\w\s-]', '', vacancy['vacancy_title'])
                vacancy_title_clean = re.sub(r'\s+', '_', vacancy_title_clean.strip())
                company_clean = re.sub(r'[^\w\s-]', '', vacancy['company'])
                company_clean = re.sub(r'\s+', '_', company_clean.strip())
                
                # Create folder structure: applications/Company_Position/version_timestamp/
                base_folder = "applications"
                vacancy_folder = f"{company_clean}_{vacancy_title_clean}"
                version_folder = f"version_{timestamp}"
                full_path = os.path.join(base_folder, vacancy_folder, version_folder)
                
                # Create directories
                os.makedirs(full_path, exist_ok=True)
                
                # File names
                resume_file = os.path.join(full_path, "resume.txt")
                cover_file = os.path.join(full_path, "cover_letter.txt")
                vacancy_info_file = os.path.join(full_path, "vacancy_info.txt")
                
                # Create vacancy info file
                vacancy_info_content = f"""VACANCY INFORMATION
==================

Position: {vacancy['vacancy_title']}
Company: {vacancy['company']}
Experience Level: {vacancy.get('experience_level', 'N/A')}
Domain: {vacancy.get('domain', 'N/A')}
Salary: {vacancy.get('salary', 'N/A')}

Required Technologies:
{vacancy.get('technologies', 'N/A')}

Required Skills:
{vacancy.get('skills', 'N/A')}

Keywords:
{vacancy.get('keywords', 'N/A')}

Vacancy URL:
{vacancy.get('url', 'N/A')}

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
                
                # Save documents
                with open(resume_file, 'w', encoding='utf-8') as f:
                    f.write(resume)
                
                with open(cover_file, 'w', encoding='utf-8') as f:
                    f.write(cover_letter)
                
                with open(vacancy_info_file, 'w', encoding='utf-8') as f:
                    f.write(vacancy_info_content)
                
                print(f"\n✅ Documents generated successfully!")
                print(f"📁 Saved in folder: {full_path}")
                print(f"📄 Resume: {resume_file}")
                print(f"📄 Cover letter: {cover_file}")
                print(f"📄 Vacancy info: {vacancy_info_file}")
                print(f"🔗 Vacancy URL: {vacancy.get('url', 'N/A')}")
                
            except ValueError:
                print("Please enter a valid number.")
            except Exception as e:
                print(f"Error generating documents: {e}")
        
        elif choice == '4':
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()