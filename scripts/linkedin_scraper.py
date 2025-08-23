#!/usr/bin/env python3
"""
Real LinkedIn Profile Scraper

Uses Selenium with stealth techniques to scrape actual LinkedIn profiles.
Bypasses anti-bot protection and extracts real professional data.

Author: Generated for ML project
Date: 2025-08-22
"""

import time
import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc
from selenium_stealth import stealth
from bs4 import BeautifulSoup
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LINKEDIN_CONFIG

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RealLinkedInScraper:
    """Real LinkedIn profile scraper using advanced stealth techniques."""
    
    def __init__(self):
        """Initialize the scraper with stealth browser."""
        self.driver = None
        self.wait = None
        self.cache_dir = "linkedin_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info("Initialized Real LinkedIn Scraper")
    
    def _setup_stealth_browser(self) -> webdriver.Chrome:
        """Setup undetected Chrome browser with stealth configuration."""
        logger.info("Setting up stealth browser...")
        
        # Chrome options for stealth
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins-discovery")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-default-apps")
        
        # User agent rotation
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        options.add_argument(f"--user-agent={user_agents[0]}")
        
        # Create undetected Chrome driver
        driver = uc.Chrome(options=options, version_main=None)
        
        # Apply stealth techniques
        stealth(driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
        )
        
        # Execute stealth scripts
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        
        logger.info("Stealth browser setup complete")
        return driver
    
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
    
    def _wait_and_scroll(self, delay: float = 2.0):
        """Wait and scroll to simulate human behavior."""
        time.sleep(delay)
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
        time.sleep(1)
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(1)
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
    
    def _extract_basic_info(self, soup: BeautifulSoup) -> Dict:
        """Extract basic profile information."""
        info = {}
        
        try:
            # Name
            name_selectors = [
                'h1.text-heading-xlarge',
                'h1[data-generated-suggestion-target]',
                '.pv-text-details__left-panel h1',
                '.ph5 h1'
            ]
            for selector in name_selectors:
                name_elem = soup.select_one(selector)
                if name_elem:
                    info['name'] = name_elem.get_text().strip()
                    break
            
            # Headline
            headline_selectors = [
                '.text-body-medium.break-words',
                '.pv-text-details__left-panel .text-body-medium',
                '.ph5 .text-body-medium'
            ]
            for selector in headline_selectors:
                headline_elem = soup.select_one(selector)
                if headline_elem:
                    info['headline'] = headline_elem.get_text().strip()
                    break
            
            # Location
            location_selectors = [
                '.text-body-small.inline.t-black--light.break-words',
                '.pv-text-details__left-panel .text-body-small',
                '.ph5 .text-body-small'
            ]
            for selector in location_selectors:
                location_elem = soup.select_one(selector)
                if location_elem:
                    info['location'] = location_elem.get_text().strip()
                    break
            
        except Exception as e:
            logger.error(f"Error extracting basic info: {e}")
        
        return info
    
    def _extract_about_section(self, soup: BeautifulSoup) -> str:
        """Extract about/summary section."""
        try:
            about_selectors = [
                '#about ~ * .pv-shared-text-with-see-more .inline-show-more-text',
                '.pv-about-section .pv-about__summary-text',
                '[data-generated-suggestion-target="urn:li:memberProfileSection"] .inline-show-more-text'
            ]
            
            for selector in about_selectors:
                about_elem = soup.select_one(selector)
                if about_elem:
                    return about_elem.get_text().strip()
            
        except Exception as e:
            logger.error(f"Error extracting about section: {e}")
        
        return ""
    
    def _extract_experience(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract work experience."""
        experiences = []
        
        try:
            # Multiple selectors for experience section
            exp_selectors = [
                '#experience ~ * .pvs-list__item--line-separated',
                '.pv-profile-section.experience-section .pv-entity__summary-info',
                '[data-generated-suggestion-target*="experience"] .pvs-list__item'
            ]
            
            for selector in exp_selectors:
                exp_items = soup.select(selector)
                if exp_items:
                    for item in exp_items[:5]:  # Limit to 5 most recent
                        exp = {}
                        
                        # Job title
                        title_elem = item.select_one('.mr1.t-bold span[aria-hidden="true"]')
                        if title_elem:
                            exp['title'] = title_elem.get_text().strip()
                        
                        # Company
                        company_elem = item.select_one('.t-14.t-normal span[aria-hidden="true"]')
                        if company_elem:
                            exp['company'] = company_elem.get_text().strip()
                        
                        # Duration
                        duration_elem = item.select_one('.t-14.t-normal.t-black--light span[aria-hidden="true"]')
                        if duration_elem:
                            exp['duration'] = duration_elem.get_text().strip()
                        
                        # Description
                        desc_elem = item.select_one('.pv-shared-text-with-see-more .inline-show-more-text')
                        if desc_elem:
                            exp['description'] = desc_elem.get_text().strip()
                        
                        if exp.get('title') and exp.get('company'):
                            experiences.append(exp)
                    
                    if experiences:
                        break
            
        except Exception as e:
            logger.error(f"Error extracting experience: {e}")
        
        return experiences
    
    def _extract_education(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract education information."""
        education = []
        
        try:
            edu_selectors = [
                '#education ~ * .pvs-list__item--line-separated',
                '.pv-profile-section.education-section .pv-entity__summary-info',
                '[data-generated-suggestion-target*="education"] .pvs-list__item'
            ]
            
            for selector in edu_selectors:
                edu_items = soup.select(selector)
                if edu_items:
                    for item in edu_items[:3]:  # Limit to 3 most recent
                        edu = {}
                        
                        # Institution
                        inst_elem = item.select_one('.mr1.t-bold span[aria-hidden="true"]')
                        if inst_elem:
                            edu['institution'] = inst_elem.get_text().strip()
                        
                        # Degree
                        degree_elem = item.select_one('.t-14.t-normal span[aria-hidden="true"]')
                        if degree_elem:
                            edu['degree'] = degree_elem.get_text().strip()
                        
                        # Duration
                        duration_elem = item.select_one('.t-14.t-normal.t-black--light span[aria-hidden="true"]')
                        if duration_elem:
                            edu['duration'] = duration_elem.get_text().strip()
                        
                        if edu.get('institution'):
                            education.append(edu)
                    
                    if education:
                        break
            
        except Exception as e:
            logger.error(f"Error extracting education: {e}")
        
        return education
    
    def _extract_skills(self, soup: BeautifulSoup) -> List[str]:
        """Extract skills."""
        skills = []
        
        try:
            skill_selectors = [
                '#skills ~ * .mr1.t-bold span[aria-hidden="true"]',
                '.pv-skill-category-entity__name span',
                '[data-generated-suggestion-target*="skills"] .mr1.t-bold span'
            ]
            
            for selector in skill_selectors:
                skill_elems = soup.select(selector)
                if skill_elems:
                    for elem in skill_elems[:15]:  # Limit to 15 skills
                        skill = elem.get_text().strip()
                        if skill and skill not in skills:
                            skills.append(skill)
                    
                    if skills:
                        break
            
        except Exception as e:
            logger.error(f"Error extracting skills: {e}")
        
        return skills
    
    def scrape_profile(self, linkedin_url: str) -> Dict:
        """
        Scrape LinkedIn profile and return structured data.
        
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
            # Setup browser
            self.driver = self._setup_stealth_browser()
            self.wait = WebDriverWait(self.driver, 20)
            
            # Navigate to profile
            logger.info("Navigating to LinkedIn profile...")
            self.driver.get(linkedin_url)
            
            # Wait for page load and simulate human behavior
            self._wait_and_scroll(3)
            
            # Check if we need to handle login or access restrictions
            if "authwall" in self.driver.current_url or "login" in self.driver.current_url:
                logger.warning("LinkedIn requires login. Attempting to access public profile data...")
                # Try to get public profile URL
                public_url = linkedin_url.replace('/in/', '/pub/').replace('www.linkedin.com', 'public.linkedin.com')
                self.driver.get(public_url)
                self._wait_and_scroll(2)
            
            # Get page source and parse with BeautifulSoup
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract profile data
            profile_data = {}
            
            # Basic info
            basic_info = self._extract_basic_info(soup)
            profile_data.update(basic_info)
            
            # About section
            profile_data['summary'] = self._extract_about_section(soup)
            
            # Experience
            profile_data['experience'] = self._extract_experience(soup)
            
            # Education
            profile_data['education'] = self._extract_education(soup)
            
            # Skills
            profile_data['skills'] = self._extract_skills(soup)
            
            # Additional fields
            profile_data['certifications'] = []
            profile_data['languages'] = ["English"]
            profile_data['projects'] = []
            
            # Validate extracted data
            if not profile_data.get('name'):
                logger.warning("Could not extract name - profile may be private or protected")
                profile_data['name'] = "Profile Private"
            
            logger.info(f"Successfully scraped profile: {profile_data.get('name', 'Unknown')}")
            
            # Save to cache
            self._save_to_cache(cache_path, profile_data)
            
            return profile_data
            
        except Exception as e:
            logger.error(f"Error scraping LinkedIn profile: {e}")
            return {
                'name': 'Scraping Failed',
                'headline': 'Could not access profile',
                'location': 'Unknown',
                'summary': 'Profile scraping failed due to access restrictions',
                'experience': [],
                'education': [],
                'skills': [],
                'certifications': [],
                'languages': ['English'],
                'projects': []
            }
        
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("Browser closed")


def main():
    """Test the LinkedIn scraper."""
    scraper = RealLinkedInScraper()
    
    # Test URL
    test_url = "https://www.linkedin.com/in/terentiy-gatskov/"
    
    try:
        profile_data = scraper.scrape_profile(test_url)
        print(json.dumps(profile_data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Scraping failed: {e}")


if __name__ == "__main__":
    main()