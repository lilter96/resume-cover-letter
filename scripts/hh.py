#!/usr/bin/env python3
"""
HeadHunter Vacancy Parser

This script parses HeadHunter (hh.ru) vacancies for Data Science and Machine Learning positions,
extracts keywords and technologies, and exports the data to CSV format.

Author: Generated for ML project
Date: 2025-08-22
"""

import requests
import pandas as pd
import time
import re
import csv
import logging
from typing import List, Dict, Set, Tuple
from collections import Counter
import json
from urllib.parse import urljoin
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hh_parser.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class HeadHunterAPI:
    """HeadHunter API client with rate limiting and error handling."""
    
    BASE_URL = "https://api.hh.ru/"
    
    def __init__(self, rate_limit_delay: float = 1.5):
        """
        Initialize API client.
        
        Args:
            rate_limit_delay: Delay between requests in seconds (1-2 recommended)
        """
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'HH-User-Agent': 'HH-Vacancy-Parser/1.0 (research purposes)'
        })
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Ensure rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Make API request with error handling and rate limiting.
        
        Args:
            endpoint: API endpoint
            params: Request parameters
            
        Returns:
            JSON response data
        """
        self._rate_limit()
        
        url = urljoin(self.BASE_URL, endpoint)
        
        try:
            response = self.session.get(url, params=params)
            logger.debug(f"Request URL: {response.url}")
            logger.debug(f"Response status: {response.status_code}")
            
            if response.status_code == 400:
                logger.error(f"Bad Request (400): {response.text}")
                return {}
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            return {}
    
    def search_vacancies(self, query: str, per_page: int = 50, max_pages: int = 5) -> List[Dict]:
        """
        Search for vacancies by query.
        
        Args:
            query: Search query
            per_page: Number of results per page (max 100)
            max_pages: Maximum number of pages to fetch
            
        Returns:
            List of vacancy data
        """
        vacancies = []
        
        for page in range(max_pages):
            params = {
                'text': query,
                'per_page': min(per_page, 100),  # API limit is 100
                'page': page,
                'area': 113  # Russia
            }
            
            logger.info(f"Fetching page {page + 1} for query: {query}")
            data = self._make_request('vacancies', params)
            
            if not data or 'items' not in data:
                logger.warning(f"No data received for page {page + 1}")
                break
                
            page_vacancies = data['items']
            if not page_vacancies:
                logger.info(f"No more vacancies found on page {page + 1}")
                break
                
            vacancies.extend(page_vacancies)
            
            # Check if we've reached the last page
            if len(page_vacancies) < per_page:
                break
        
        logger.info(f"Found {len(vacancies)} vacancies for query: {query}")
        return vacancies
    
    def get_vacancy_details(self, vacancy_id: str) -> Dict:
        """
        Get detailed vacancy information.
        
        Args:
            vacancy_id: Vacancy ID
            
        Returns:
            Detailed vacancy data
        """
        return self._make_request(f'vacancies/{vacancy_id}')


class OpenRouterLLM:
    """OpenRouter LLM client for intelligent text analysis."""
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize OpenRouter LLM client.
        
        Args:
            api_key: OpenRouter API key (defaults to env var)
            model: Model to use (defaults to claude-3-haiku)
        """
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.model = model or os.getenv('OPENROUTER_MODEL', 'anthropic/claude-3-haiku')
        self.app_name = os.getenv('OPENROUTER_APP_NAME', 'HeadHunter-Vacancy-Parser')
        self.app_url = os.getenv('OPENROUTER_APP_URL', 'https://github.com/user/hh-parser')
        
        if not self.api_key:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable.")
        
        # Initialize OpenAI client with OpenRouter endpoint
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
            default_headers={
                "HTTP-Referer": self.app_url,
                "X-Title": self.app_name,
            }
        )
        
        logger.info(f"Initialized OpenRouter LLM with model: {self.model}")
    
    def extract_job_info(self, job_text: str) -> Dict:
        """
        Extract structured information from job description using LLM.
        
        Args:
            job_text: Raw job description text
            
        Returns:
            Dictionary with extracted keywords, technologies, skills, etc.
        """
        prompt = self._create_extraction_prompt(job_text)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing job descriptions for Data Science and Machine Learning positions. Extract structured information accurately and comprehensively."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content
            return self._parse_llm_response(result_text)
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return {
                'keywords': [],
                'technologies': [],
                'skills': [],
                'experience_level': 'Unknown',
                'domain': 'Unknown'
            }
    
    def _create_extraction_prompt(self, job_text: str) -> str:
        """Create a structured prompt for job information extraction."""
        return f"""
Analyze the following job description and extract structured information. Return the results in JSON format with these exact keys:

1. "keywords": List of relevant ML/DS keywords (e.g., "machine learning", "data science", "artificial intelligence", "deep learning", "nlp", "computer vision", "mlops", "data analysis", "big data", "statistics", "predictive modeling", "feature engineering", "model deployment")

2. "technologies": List of specific technologies, tools, frameworks, and programming languages mentioned (e.g., "python", "r", "sql", "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "docker", "kubernetes", "aws", "azure", "spark", "airflow", "jupyter", "git")

3. "skills": List of soft skills and domain expertise (e.g., "communication", "teamwork", "problem-solving", "analytical thinking", "business acumen", "research", "experimentation")

4. "experience_level": One of "Junior", "Middle", "Senior", "Lead", "Principal", or "Unknown"

5. "domain": Primary domain/industry focus (e.g., "Finance", "Healthcare", "E-commerce", "Automotive", "General", "Unknown")

Job Description:
{job_text}

Return only valid JSON without any additional text or formatting:
"""
    
    def _parse_llm_response(self, response_text: str) -> Dict:
        """Parse LLM response and extract structured data."""
        try:
            # Try to extract JSON from the response
            response_text = response_text.strip()
            
            # Find JSON content between curly braces
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_text = response_text[start_idx:end_idx]
                parsed_data = json.loads(json_text)
                
                # Ensure all required keys exist
                default_data = {
                    'keywords': [],
                    'technologies': [],
                    'skills': [],
                    'experience_level': 'Unknown',
                    'domain': 'Unknown'
                }
                
                # Merge with defaults
                for key in default_data:
                    if key not in parsed_data:
                        parsed_data[key] = default_data[key]
                
                # Ensure lists are actually lists
                for key in ['keywords', 'technologies', 'skills']:
                    if not isinstance(parsed_data[key], list):
                        parsed_data[key] = []
                
                return parsed_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
        
        # Return default structure if parsing fails
        return {
            'keywords': [],
            'technologies': [],
            'skills': [],
            'experience_level': 'Unknown',
            'domain': 'Unknown'
        }


class VacancyProcessor:
    """Process vacancy data and extract keywords/technologies using LLM."""
    
    def __init__(self, use_llm: bool = True):
        """
        Initialize vacancy processor.
        
        Args:
            use_llm: Whether to use LLM for extraction (default: True)
        """
        self.use_llm = use_llm
        self.all_keywords = Counter()
        self.all_technologies = Counter()
        self.all_skills = Counter()
        self.all_experience_levels = Counter()
        self.all_domains = Counter()
        
        if self.use_llm:
            try:
                self.llm = OpenRouterLLM()
                logger.info("LLM-powered extraction enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM: {e}. Falling back to regex extraction.")
                self.use_llm = False
                self._init_regex_patterns()
        else:
            self._init_regex_patterns()
    
    def _init_regex_patterns(self):
        """Initialize regex patterns as fallback."""
        # Common ML/DS technologies and tools
        self.TECHNOLOGIES = {
            'python', 'r', 'sql', 'scala', 'java', 'c++', 'julia',
            'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'sklearn',
            'pandas', 'numpy', 'scipy', 'matplotlib', 'seaborn', 'plotly',
            'jupyter', 'anaconda', 'docker', 'kubernetes', 'git',
            'spark', 'hadoop', 'kafka', 'airflow', 'mlflow',
            'aws', 'azure', 'gcp', 'google cloud', 'amazon web services',
            'tableau', 'power bi', 'qlik', 'looker',
            'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
            'fastapi', 'flask', 'django', 'streamlit', 'dash',
            'xgboost', 'lightgbm', 'catboost', 'opencv', 'nltk', 'spacy',
            'bert', 'transformers', 'hugging face', 'openai', 'langchain'
        }
        
        # Common ML/DS keywords
        self.KEYWORDS_PATTERNS = [
            r'\bmachine learning\b', r'\bml\b', r'\bdeep learning\b', r'\bdl\b',
            r'\bdata science\b', r'\bdata scientist\b', r'\bdata analysis\b',
            r'\bartificial intelligence\b', r'\bai\b', r'\bneural network\b',
            r'\bcomputer vision\b', r'\bcv\b', r'\bnlp\b', r'\bnatural language processing\b',
            r'\bbig data\b', r'\betl\b', r'\bdata mining\b', r'\bstatistics\b',
            r'\bpredictive modeling\b', r'\bregression\b', r'\bclassification\b',
            r'\bclustering\b', r'\brecommendation system\b', r'\btime series\b',
            r'\ba/b testing\b', r'\bexperiment design\b', r'\bfeature engineering\b',
            r'\bmodel deployment\b', r'\bmlops\b', r'\bdata pipeline\b',
            r'\bvisualization\b', r'\bdashboard\b', r'\breporting\b'
        ]
    
    def extract_text_content(self, vacancy: Dict) -> str:
        """Extract all text content from vacancy for analysis."""
        text_parts = []
        
        # Add name/title
        if vacancy.get('name'):
            text_parts.append(vacancy['name'])
        
        # Add description
        if vacancy.get('description'):
            # Remove HTML tags
            description = re.sub(r'<[^>]+>', ' ', vacancy['description'])
            text_parts.append(description)
        
        # Add key skills
        if vacancy.get('key_skills'):
            skills = [skill.get('name', '') for skill in vacancy['key_skills']]
            text_parts.extend(skills)
        
        # Add professional roles
        if vacancy.get('professional_roles'):
            roles = [role.get('name', '') for role in vacancy['professional_roles']]
            text_parts.extend(roles)
        
        return ' '.join(text_parts).lower()
    
    def extract_with_llm(self, text: str) -> Dict:
        """Extract information using LLM."""
        if not self.use_llm:
            return self.extract_with_regex(text)
        
        try:
            return self.llm.extract_job_info(text)
        except Exception as e:
            logger.error(f"LLM extraction failed, falling back to regex: {e}")
            return self.extract_with_regex(text)
    
    def extract_with_regex(self, text: str) -> Dict:
        """Extract information using regex patterns (fallback)."""
        technologies = self.extract_technologies_regex(text)
        keywords = self.extract_keywords_regex(text)
        
        return {
            'keywords': list(keywords),
            'technologies': list(technologies),
            'skills': [],
            'experience_level': 'Unknown',
            'domain': 'Unknown'
        }
    
    def extract_technologies_regex(self, text: str) -> Set[str]:
        """Extract technologies from text using regex."""
        found_techs = set()
        text_lower = text.lower()
        
        for tech in self.TECHNOLOGIES:
            # Use word boundaries for better matching
            pattern = r'\b' + re.escape(tech.lower()) + r'\b'
            if re.search(pattern, text_lower):
                found_techs.add(tech)
        
        return found_techs
    
    def extract_keywords_regex(self, text: str) -> Set[str]:
        """Extract ML/DS keywords from text using regex."""
        found_keywords = set()
        text_lower = text.lower()
        
        for pattern in self.KEYWORDS_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            found_keywords.update(matches)
        
        return found_keywords
    
    def process_vacancy(self, vacancy: Dict) -> Dict:
        """
        Process a single vacancy and extract relevant information.
        
        Args:
            vacancy: Raw vacancy data from API
            
        Returns:
            Processed vacancy data
        """
        text_content = self.extract_text_content(vacancy)
        
        # Extract information using LLM or regex
        extracted_info = self.extract_with_llm(text_content)
        
        # Update global counters
        self.all_keywords.update(extracted_info['keywords'])
        self.all_technologies.update(extracted_info['technologies'])
        self.all_skills.update(extracted_info['skills'])
        self.all_experience_levels[extracted_info['experience_level']] += 1
        self.all_domains[extracted_info['domain']] += 1
        
        # Extract salary information
        salary_info = ""
        if vacancy.get('salary'):
            salary = vacancy['salary']
            salary_from = salary.get('from', '')
            salary_to = salary.get('to', '')
            currency = salary.get('currency', '')
            
            if salary_from and salary_to:
                salary_info = f"{salary_from}-{salary_to} {currency}"
            elif salary_from:
                salary_info = f"от {salary_from} {currency}"
            elif salary_to:
                salary_info = f"до {salary_to} {currency}"
        
        # Extract company name
        company_name = ""
        if vacancy.get('employer'):
            company_name = vacancy['employer'].get('name', '')
        
        return {
            'vacancy_title': vacancy.get('name', ''),
            'company': company_name,
            'keywords': ', '.join(sorted(extracted_info['keywords'])),
            'technologies': ', '.join(sorted(extracted_info['technologies'])),
            'skills': ', '.join(sorted(extracted_info['skills'])),
            'experience_level': extracted_info['experience_level'],
            'domain': extracted_info['domain'],
            'salary': salary_info,
            'url': vacancy.get('alternate_url', '')
        }
    
    def get_frequency_stats(self) -> Dict[str, List[Tuple[str, int]]]:
        """Get frequency statistics for all extracted categories."""
        return {
            'keywords': self.all_keywords.most_common(20),
            'technologies': self.all_technologies.most_common(20),
            'skills': self.all_skills.most_common(20),
            'experience_levels': self.all_experience_levels.most_common(10),
            'domains': self.all_domains.most_common(10)
        }


class CSVExporter:
    """Export processed vacancy data to CSV."""
    
    @staticmethod
    def export_vacancies(vacancies: List[Dict], filename: str = 'hh_vacancies.csv'):
        """
        Export vacancies to CSV file.
        
        Args:
            vacancies: List of processed vacancy data
            filename: Output filename
        """
        if not vacancies:
            logger.warning("No vacancies to export")
            return
        
        fieldnames = [
            'vacancy_title', 'company', 'keywords', 'technologies', 'skills',
            'experience_level', 'domain', 'salary', 'url'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(vacancies)
        
        logger.info(f"Exported {len(vacancies)} vacancies to {filename}")
    
    @staticmethod
    def export_frequency_stats(stats: Dict[str, List[Tuple[str, int]]],
                             filename: str = 'hh_frequency_stats.csv'):
        """
        Export frequency statistics to CSV.
        
        Args:
            stats: Dictionary with frequency statistics for different categories
            filename: Output filename
        """
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            sections = [
                ('Top Keywords', 'keywords'),
                ('Top Technologies', 'technologies'),
                ('Top Skills', 'skills'),
                ('Experience Levels', 'experience_levels'),
                ('Domains', 'domains')
            ]
            
            for i, (title, key) in enumerate(sections):
                if i > 0:  # Add empty row separator
                    writer.writerow([])
                
                writer.writerow([title])
                writer.writerow([key.replace('_', ' ').title(), 'Frequency'])
                
                if key in stats:
                    writer.writerows(stats[key])
        
        logger.info(f"Exported frequency statistics to {filename}")


def main():
    """Main function to run the HeadHunter vacancy parser."""
    logger.info("Starting HeadHunter vacancy parser")
    
    # Initialize components
    api = HeadHunterAPI(rate_limit_delay=1.5)
    processor = VacancyProcessor()
    exporter = CSVExporter()
    
    # Search queries (reduced for testing)
    queries = [
        "Data Scientist"
    ]
    
    all_processed_vacancies = []
    
    try:
        for query in queries:
            logger.info(f"Processing query: {query}")
            
            # Search for vacancies (limited for testing - 5 per query)
            vacancies = api.search_vacancies(query, per_page=5, max_pages=1)
            
            # Get detailed information for each vacancy
            total_vacancies = len(vacancies)
            logger.info(f"Fetching detailed information for {total_vacancies} vacancies...")
            
            for i, vacancy in enumerate(vacancies, 1):
                vacancy_id = vacancy.get('id')
                if vacancy_id:
                    vacancy_name = vacancy.get('name', 'Unknown')[:50]
                    logger.info(f"Processing vacancy {i}/{total_vacancies}: {vacancy_name}...")
                    
                    detailed_vacancy = api.get_vacancy_details(vacancy_id)
                    if detailed_vacancy:
                        processed = processor.process_vacancy(detailed_vacancy)
                        all_processed_vacancies.append(processed)
                    else:
                        logger.warning(f"Failed to get details for vacancy {vacancy_id}")
                
                # Progress update every 10 vacancies
                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{total_vacancies} vacancies processed for query '{query}'")
        
        # Remove duplicates based on URL
        unique_vacancies = []
        seen_urls = set()
        for vacancy in all_processed_vacancies:
            url = vacancy['url']
            if url not in seen_urls:
                unique_vacancies.append(vacancy)
                seen_urls.add(url)
        
        logger.info(f"Total unique vacancies processed: {len(unique_vacancies)}")
        
        # Export results
        exporter.export_vacancies(unique_vacancies, 'hh_vacancies.csv')
        
        # Get and export frequency statistics
        frequency_stats = processor.get_frequency_stats()
        exporter.export_frequency_stats(frequency_stats, 'hh_frequency_stats.csv')
        
        # Print summary
        print(f"\n=== SUMMARY ===")
        print(f"Total vacancies processed: {len(unique_vacancies)}")
        print(f"Results exported to: hh_vacancies.csv")
        print(f"Frequency stats exported to: hh_frequency_stats.csv")
        
        print(f"\nTop 10 Technologies:")
        for tech, count in frequency_stats['technologies'][:10]:
            print(f"  {tech}: {count}")
        
        print(f"\nTop 10 Keywords:")
        for keyword, count in frequency_stats['keywords'][:10]:
            print(f"  {keyword}: {count}")
        
        print(f"\nTop 5 Skills:")
        for skill, count in frequency_stats['skills'][:5]:
            print(f"  {skill}: {count}")
        
        print(f"\nExperience Levels:")
        for level, count in frequency_stats['experience_levels']:
            print(f"  {level}: {count}")
        
        print(f"\nDomains:")
        for domain, count in frequency_stats['domains']:
            print(f"  {domain}: {count}")
        
    except Exception as e:
        logger.error(f"Error during execution: {e}")
        raise


if __name__ == "__main__":
    main()