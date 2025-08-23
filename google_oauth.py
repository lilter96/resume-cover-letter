"""
Google OAuth Service for Resume Generator
Handles Google OAuth authentication flow
"""

import os
import json
from typing import Optional, Dict, Any
from urllib.parse import urlencode
import httpx
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.base_client import OAuthError
from starlette.config import Config
from starlette.requests import Request
from dotenv import load_dotenv

load_dotenv()

class GoogleOAuthService:
    """Service for handling Google OAuth authentication."""
    
    def __init__(self):
        """Initialize Google OAuth service."""
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/auth/google/callback')
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth credentials not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.")
        
        # OAuth configuration
        config = Config(environ={
            'GOOGLE_CLIENT_ID': self.client_id,
            'GOOGLE_CLIENT_SECRET': self.client_secret
        })
        
        self.oauth = OAuth(config)
        self.oauth.register(
            name='google',
            client_id=self.client_id,
            client_secret=self.client_secret,
            server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
            client_kwargs={
                'scope': 'openid email profile'
            }
        )
        
        self.google_client = self.oauth.google
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate Google OAuth authorization URL."""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'openid email profile',
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        if state:
            params['state'] = state
        
        return f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token."""
        try:
            async with httpx.AsyncClient() as client:
                token_data = {
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'code': code,
                    'grant_type': 'authorization_code',
                    'redirect_uri': self.redirect_uri
                }
                
                response = await client.post(
                    'https://oauth2.googleapis.com/token',
                    data=token_data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"Token exchange failed: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            print(f"Error exchanging code for token: {e}")
            return None
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from Google using access token."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://www.googleapis.com/oauth2/v2/userinfo',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"User info request failed: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            print(f"Error getting user info: {e}")
            return None
    
    async def authenticate_user(self, code: str) -> Optional[Dict[str, Any]]:
        """Complete OAuth flow and return user information."""
        # Exchange code for token
        token_data = await self.exchange_code_for_token(code)
        if not token_data or 'access_token' not in token_data:
            return None
        
        # Get user information
        user_info = await self.get_user_info(token_data['access_token'])
        if not user_info:
            return None
        
        # Return combined data
        return {
            'user_info': user_info,
            'token_data': token_data
        }
    
    def extract_user_data(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant user data from Google user info."""
        return {
            'email': user_info.get('email'),
            'name': user_info.get('name'),
            'given_name': user_info.get('given_name'),
            'family_name': user_info.get('family_name'),
            'picture': user_info.get('picture'),
            'google_id': user_info.get('id'),
            'verified_email': user_info.get('verified_email', False)
        }
    
    def is_configured(self) -> bool:
        """Check if Google OAuth is properly configured."""
        return bool(self.client_id and self.client_secret)

# Global instance
google_oauth_service = None

def get_google_oauth_service() -> Optional[GoogleOAuthService]:
    """Get Google OAuth service instance."""
    global google_oauth_service
    
    if google_oauth_service is None:
        try:
            google_oauth_service = GoogleOAuthService()
        except ValueError as e:
            print(f"Google OAuth not configured: {e}")
            return None
    
    return google_oauth_service