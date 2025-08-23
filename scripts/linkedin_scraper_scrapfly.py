#!/usr/bin/env python3
"""
LinkedIn Profile Scraper using Scrapfly Approach

Uses httpx and parsel to scrape LinkedIn profiles without browser automation.
Based on the Scrapfly guide for LinkedIn scraping in 2025.

Author: Generated for ML project
Date: 2025-08-22
"""

import json
import time
import re
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging
import httpx
from parsel import Selector
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LINKEDIN_CONFIG

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LinkedInScrapflyScraper:
    """LinkedIn profile scraper using Scrapfly approach without browser automation."""
    
    def __init__(self):
        """Initialize the scraper with HTTP client."""
        self.cache_dir = "linkedin_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Setup HTTP client with realistic headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        self.client = httpx.Client(
            headers=self.headers,
            timeout=30.0,
            follow_redirects=True
        )
        
        logger.info("Initialized LinkedIn Scrapfly Scraper")
    
    def _get_cache_path(self, linkedin_url: str) -> str:
        """Get cache file path for specific LinkedIn URL."""
        url_hash = str(abs(hash(linkedin_url)))
        return os.path.join(self.cache_dir, f"profile_{url_hash}.json")
    
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
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text.strip())
    
    def _extract_json_ld(self, selector: Selector) -> Dict:
        """Extract JSON-LD structured data from LinkedIn profile."""
        try:
            json_ld_text = selector.xpath("//script[@type='application/ld+json']/text()").get()
            if json_ld_text:
                data = json.loads(json_ld_text)
                logger.info("Successfully extracted JSON-LD data")
                return data
        except Exception as e:
            logger.error(f"Failed to extract JSON-LD: {e}")
        return {}
    
    def _parse_profile_from_json_ld(self, json_data: Dict) -> Dict:
        """Parse profile data from JSON-LD structured data."""
        profile_data = {
            'name': '',
            'headline': '',
            'location': '',
            'summary': '',
            'experience': [],
            'education': [],
            'skills': [],
            'certifications': [],
            'languages': ['English'],
            'projects': []
        }
        
        try:
            # Handle different JSON-LD structures
            if '@graph' in json_data:
                # Multiple entities in @graph
                for item in json_data['@graph']:
                    if item.get('@type') == 'Person':
                        profile_data['name'] = item.get('name', '')
                        profile_data['headline'] = item.get('jobTitle', '')
                        
                        # Location
                        if 'address' in item:
                            address = item['address']
                            if isinstance(address, dict):
                                location_parts = []
                                if 'addressLocality' in address:
                                    location_parts.append(address['addressLocality'])
                                if 'addressCountry' in address:
                                    location_parts.append(address['addressCountry'])
                                profile_data['location'] = ', '.join(location_parts)
                        
                        # Work experience
                        if 'worksFor' in item:
                            works_for = item['worksFor']
                            if isinstance(works_for, list) and works_for:
                                works_for = works_for[0]
                            if isinstance(works_for, dict):
                                profile_data['experience'].append({
                                    'title': item.get('jobTitle', ''),
                                    'company': works_for.get('name', ''),
                                    'duration': 'Present',
                                    'description': ''
                                })
                    
                    elif item.get('@type') == 'Article':
                        # LinkedIn posts/articles
                        if 'articleBody' in item:
                            # Could extract insights from posts
                            pass
            
            else:
                # Single entity
                if json_data.get('@type') == 'Person':
                    profile_data['name'] = json_data.get('name', '')
                    profile_data['headline'] = json_data.get('jobTitle', '')
                    
                    # Location
                    if 'address' in json_data:
                        address = json_data['address']
                        if isinstance(address, dict):
                            location_parts = []
                            if 'addressLocality' in address:
                                location_parts.append(address['addressLocality'])
                            if 'addressCountry' in address:
                                location_parts.append(address['addressCountry'])
                            profile_data['location'] = ', '.join(location_parts)
            
        except Exception as e:
            logger.error(f"Error parsing JSON-LD data: {e}")
        
        return profile_data
    
    def _parse_profile_from_html(self, selector: Selector) -> Dict:
        """Parse profile data from HTML elements."""
        profile_data = {
            'name': '',
            'headline': '',
            'location': '',
            'summary': '',
            'experience': [],
            'education': [],
            'skills': [],
            'certifications': [],
            'languages': ['English'],
            'projects': []
        }
        
        try:
            # Name - try multiple selectors
            name_selectors = [
                'h1.text-heading-xlarge::text',
                'h1[data-generated-suggestion-target]::text',
                '.pv-text-details__left-panel h1::text',
                '.ph5 h1::text',
                'h1::text'
            ]
            for selector_str in name_selectors:
                name = selector.css(selector_str).get()
                if name:
                    profile_data['name'] = self._clean_text(name)
                    break
            
            # Headline
            headline_selectors = [
                '.text-body-medium.break-words::text',
                '.pv-text-details__left-panel .text-body-medium::text',
                '.ph5 .text-body-medium::text'
            ]
            for selector_str in headline_selectors:
                headline = selector.css(selector_str).get()
                if headline:
                    profile_data['headline'] = self._clean_text(headline)
                    break
            
            # Location
            location_selectors = [
                '.text-body-small.inline.t-black--light.break-words::text',
                '.pv-text-details__left-panel .text-body-small::text',
                '.ph5 .text-body-small::text'
            ]
            for selector_str in location_selectors:
                location = selector.css(selector_str).get()
                if location:
                    profile_data['location'] = self._clean_text(location)
                    break
            
            # About/Summary
            about_selectors = [
                '#about ~ * .pv-shared-text-with-see-more .inline-show-more-text::text',
                '.pv-about-section .pv-about__summary-text::text',
                '[data-generated-suggestion-target*="about"] .inline-show-more-text::text'
            ]
            for selector_str in about_selectors:
                about = selector.css(selector_str).getall()
                if about:
                    profile_data['summary'] = self._clean_text(' '.join(about))
                    break
            
            # Experience - basic extraction
            exp_items = selector.css('#experience ~ * .pvs-list__item--line-separated, .pv-profile-section.experience-section .pv-entity__summary-info')
            for item in exp_items[:5]:  # Limit to 5 most recent
                title = item.css('.mr1.t-bold span::text').get()
                company = item.css('.t-14.t-normal span::text').get()
                duration = item.css('.t-14.t-normal.t-black--light span::text').get()
                
                if title and company:
                    profile_data['experience'].append({
                        'title': self._clean_text(title),
                        'company': self._clean_text(company),
                        'duration': self._clean_text(duration) if duration else '',
                        'description': ''
                    })
            
            # Skills - basic extraction
            skill_items = selector.css('#skills ~ * .mr1.t-bold span::text, .pv-skill-category-entity__name span::text').getall()
            profile_data['skills'] = [self._clean_text(skill) for skill in skill_items[:15] if skill.strip()]
            
        except Exception as e:
            logger.error(f"Error parsing HTML data: {e}")
        
        return profile_data
    
    def _merge_profile_data(self, json_data: Dict, html_data: Dict) -> Dict:
        """Merge data from JSON-LD and HTML parsing."""
        merged = html_data.copy()
        
        # Prefer JSON-LD data when available and more complete
        for key in ['name', 'headline', 'location', 'summary']:
            if json_data.get(key) and len(json_data[key]) > len(merged.get(key, '')):
                merged[key] = json_data[key]
        
        # Merge experience
        if json_data.get('experience') and not merged.get('experience'):
            merged['experience'] = json_data['experience']
        
        return merged
    
    def scrape_profile(self, linkedin_url: str) -> Dict:
        """
        Scrape LinkedIn profile using Scrapfly approach.
        
        Args:
            linkedin_url: LinkedIn profile URL
            
        Returns:
            Structured profile data
        """
        cache_path = self._get_cache_path(linkedin_url)
        
        # Check cache first
        if self._is_cache_valid(cache_path):
            cached_data = self._load_from_cache(cache_path)
            if cached_data:
                return cached_data
        
        logger.info(f"Scraping LinkedIn profile: {linkedin_url}")
        
        try:
            # Add delay to be respectful
            time.sleep(2)
            
            # Request the profile page
            response = self.client.get(linkedin_url)
            response.raise_for_status()
            
            # Parse with Selector
            selector = Selector(response.text)
            
            # Extract data using both methods
            json_ld_data = self._extract_json_ld(selector)
            json_profile = self._parse_profile_from_json_ld(json_ld_data)
            html_profile = self._parse_profile_from_html(selector)
            
            # Merge the data
            profile_data = self._merge_profile_data(json_profile, html_profile)
            
            # Validate and enhance
            if not profile_data.get('name'):
                profile_data['name'] = "Profile Access Limited"
                logger.warning("Could not extract name - profile may be private")
            
            if not profile_data.get('headline'):
                profile_data['headline'] = "Professional"
            
            if not profile_data.get('location'):
                profile_data['location'] = "Location not specified"
            
            # Add default values for missing fields
            if not profile_data.get('skills'):
                profile_data['skills'] = []
            
            if not profile_data.get('experience'):
                profile_data['experience'] = []
            
            if not profile_data.get('education'):
                profile_data['education'] = []
            
            logger.info(f"Successfully scraped profile: {profile_data.get('name', 'Unknown')}")
            
            # Save to cache
            self._save_to_cache(cache_path, profile_data)
            
            return profile_data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error scraping LinkedIn profile: {e}")
            return self._get_fallback_profile(f"HTTP Error: {e.response.status_code}")
        
        except Exception as e:
            logger.error(f"Error scraping LinkedIn profile: {e}")
            return self._get_fallback_profile(f"Scraping Error: {str(e)}")
        
        finally:
            # Close client if needed
            pass
    
    def _get_fallback_profile(self, error_msg: str = "Access Limited") -> Dict:
        """Get fallback profile data when scraping fails."""
        return {
            'name': f'Profile Access Limited ({error_msg})',
            'headline': 'Could not access profile details',
            'location': 'Unknown',
            'summary': 'Profile information could not be accessed due to privacy settings or access restrictions.',
            'experience': [],
            'education': [],
            'skills': [],
            'certifications': [],
            'languages': ['English'],
            'projects': []
        }
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()


def main():
    """Test the LinkedIn scraper."""
    scraper = LinkedInScrapflyScraper()
    
    try:
        # Test URL
        test_url = "https://www.linkedin.com/in/terentiy-gatskov/"
        
        profile_data = scraper.scrape_profile(test_url)
        print(json.dumps(profile_data, indent=2, ensure_ascii=False))
    
    except Exception as e:
        print(f"Scraping failed: {e}")
    
    finally:
        scraper.close()


if __name__ == "__main__":
    main()