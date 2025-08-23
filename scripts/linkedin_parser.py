#!/usr/bin/env python3
"""
LinkedIn Profile Parser

Parses LinkedIn profiles to extract professional information for resume generation.
Uses LLM for intelligent data extraction and caching for performance.

Author: Generated for ML project
Date: 2025-08-22
"""

import requests
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging
from dotenv import load_dotenv
from openai import OpenAI
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LINKEDIN_CONFIG, USER_PROFILE

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LinkedInParser:
    """Parse LinkedIn profiles using real scraping and LLM enhancement."""
    
    def __init__(self):
        """Initialize the LinkedIn parser."""
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            logger.warning("OpenRouter API key not found - LLM enhancement disabled")
            self.client = None
        else:
            self.model = os.getenv('OPENROUTER_MODEL', 'anthropic/claude-3-haiku')
            self.app_name = os.getenv('OPENROUTER_APP_NAME', 'LinkedIn-Parser')
            self.app_url = os.getenv('OPENROUTER_APP_URL', 'https://github.com/user/linkedin-parser')
            
            # Initialize OpenAI client with OpenRouter endpoint
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key,
                default_headers={
                    "HTTP-Referer": self.app_url,
                    "X-Title": self.app_name,
                }
            )
        
        # Initialize Scrapfly scraper
        self.scraper = LinkedInScrapflyScraper()
        self.cache_file = 'linkedin_cache.json'
        logger.info("Initialized LinkedIn Parser with Scrapfly scraping + LLM enhancement")
    
    def _get_cache_path(self, linkedin_url: str) -> str:
        """Get cache file path for specific LinkedIn URL."""
        url_hash = str(hash(linkedin_url))
        return f"linkedin_cache_{url_hash}.json"
    
    def _is_cache_valid(self, cache_path: str) -> bool:
        """Check if cached data is still valid."""
        if not os.path.exists(cache_path):
            return False
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            cache_time = datetime.fromisoformat(cache_data.get('cached_at', ''))
            expiry_time = cache_time + timedelta(hours=LINKEDIN_CONFIG['cache_duration_hours'])
            
            return datetime.now() < expiry_time
        except Exception as e:
            logger.warning(f"Cache validation failed: {e}")
            return False
    
    def _load_from_cache(self, cache_path: str) -> Optional[Dict]:
        """Load profile data from cache."""
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            logger.info("Loaded LinkedIn profile from cache")
            return cache_data.get('profile_data')
        except Exception as e:
            logger.error(f"Failed to load from cache: {e}")
            return None
    
    def _save_to_cache(self, cache_path: str, profile_data: Dict):
        """Save profile data to cache."""
        try:
            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'profile_data': profile_data
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            logger.info("Saved LinkedIn profile to cache")
        except Exception as e:
            logger.error(f"Failed to save to cache: {e}")
    
    def _enhance_with_llm(self, scraped_data: Dict) -> Dict:
        """Enhance scraped data with LLM processing."""
        if not self.client:
            logger.info("LLM enhancement disabled - returning scraped data as-is")
            return scraped_data
        
        prompt = f"""
Enhance and clean the following LinkedIn profile data that was scraped from a real profile.
Fix any formatting issues, expand abbreviations, and improve the professional descriptions.

SCRAPED DATA:
{json.dumps(scraped_data, indent=2)}

Return the enhanced data in the same JSON structure, but with:
1. Cleaned and properly formatted text
2. Expanded abbreviations and technical terms
3. More professional descriptions where needed
4. Consistent formatting
5. Additional relevant skills if the current list seems incomplete

Keep all the real data intact - only enhance and clean it, don't make up new information.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are enhancing real LinkedIn profile data. Clean and improve the text while keeping all factual information intact."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=2000
            )
            
            result = response.choices[0].message.content
            
            # Try to parse JSON from the response
            try:
                json_start = result.find('{')
                json_end = result.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    json_str = result[json_start:json_end]
                    enhanced_data = json.loads(json_str)
                    logger.info("Successfully enhanced scraped data with LLM")
                    return enhanced_data
                else:
                    logger.warning("Could not parse LLM enhancement - returning original data")
                    return scraped_data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM enhancement: {e}")
                return scraped_data
                
        except Exception as e:
            logger.error(f"LLM enhancement failed: {e}")
            return scraped_data
    
    def _get_fallback_profile(self) -> Dict:
        """Get fallback profile data when parsing fails."""
        return {
            "name": USER_PROFILE.get('name', 'Unknown'),
            "headline": f"{USER_PROFILE.get('current_position', 'ML Engineer')} | Data Science Enthusiast",
            "location": USER_PROFILE.get('location', 'Unknown'),
            "summary": f"Experienced {USER_PROFILE.get('current_position', 'ML Engineer')} with {USER_PROFILE.get('experience_years', '1')} years in machine learning and data science.",
            "experience": [
                {
                    "title": USER_PROFILE.get('current_position', 'ML Engineer'),
                    "company": "Tech Company",
                    "duration": f"{2024 - int(USER_PROFILE.get('experience_years', 1))} - Present",
                    "description": USER_PROFILE.get('achievements', 'Developed ML models and improved system performance')
                }
            ],
            "education": [
                {
                    "institution": USER_PROFILE.get('education', 'University'),
                    "degree": "Bachelor's in Computer Science",
                    "duration": "2020 - 2024"
                }
            ],
            "skills": USER_PROFILE.get('key_skills', ['python', 'machine learning']),
            "certifications": [],
            "languages": ["English", "Russian"],
            "projects": []
        }
    
    def parse_profile(self, linkedin_url: str) -> Dict:
        """
        Parse LinkedIn profile and return structured data.
        
        Args:
            linkedin_url: LinkedIn profile URL
            
        Returns:
            Structured profile data
        """
        if not LINKEDIN_CONFIG['enabled']:
            logger.info("LinkedIn parsing disabled, using fallback profile")
            return self._get_fallback_profile()
        
        cache_path = self._get_cache_path(linkedin_url)
        
        # Check cache first
        if self._is_cache_valid(cache_path):
            cached_data = self._load_from_cache(cache_path)
            if cached_data:
                return cached_data
        
        logger.info(f"Parsing LinkedIn profile: {linkedin_url}")
        
        # Fetch and parse profile
        html_content = self._fetch_linkedin_content(linkedin_url)
        profile_data = self._extract_with_llm(html_content, linkedin_url)
        
        # Save to cache
        self._save_to_cache(cache_path, profile_data)
        
        return profile_data
    
    def enhance_user_profile(self, base_profile: Dict, linkedin_url: str = None) -> Dict:
        """
        Enhance user profile with LinkedIn data.
        
        Args:
            base_profile: Base user profile from config
            linkedin_url: LinkedIn URL (optional, uses config if not provided)
            
        Returns:
            Enhanced profile with LinkedIn data
        """
        if not linkedin_url:
            linkedin_url = base_profile.get('linkedin')
        
        if not linkedin_url:
            logger.warning("No LinkedIn URL provided, using base profile")
            return base_profile
        
        try:
            linkedin_data = self.parse_profile(linkedin_url)
            
            # Merge LinkedIn data with base profile
            enhanced_profile = base_profile.copy()
            enhanced_profile.update({
                'linkedin_data': linkedin_data,
                'enhanced_summary': linkedin_data.get('summary', ''),
                'linkedin_experience': linkedin_data.get('experience', []),
                'linkedin_education': linkedin_data.get('education', []),
                'linkedin_skills': linkedin_data.get('skills', []),
                'linkedin_projects': linkedin_data.get('projects', []),
                'linkedin_certifications': linkedin_data.get('certifications', [])
            })
            
            logger.info("Successfully enhanced profile with LinkedIn data")
            return enhanced_profile
            
        except Exception as e:
            logger.error(f"Failed to enhance profile with LinkedIn: {e}")
            return base_profile


def main():
    """Test LinkedIn parser."""
    parser = LinkedInParser()
    
    # Test with user's LinkedIn URL
    linkedin_url = USER_PROFILE.get('linkedin')
    if linkedin_url:
        profile_data = parser.parse_profile(linkedin_url)
        print(json.dumps(profile_data, indent=2, ensure_ascii=False))
    else:
        print("No LinkedIn URL found in user profile")


if __name__ == "__main__":
    main()