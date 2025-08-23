# Google OAuth Setup Guide

This guide explains how to set up Google OAuth authentication for the Resume Generator application.

## Prerequisites

- Google Cloud Console account
- Resume Generator application running locally or deployed

## Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" and then "New Project"
3. Enter a project name (e.g., "Resume Generator OAuth")
4. Click "Create"

## Step 2: Enable Google+ API

1. In the Google Cloud Console, go to "APIs & Services" > "Library"
2. Search for "Google+ API" or "People API"
3. Click on it and press "Enable"

## Step 3: Configure OAuth Consent Screen

1. Go to "APIs & Services" > "OAuth consent screen"
2. Choose "External" user type (unless you have a Google Workspace account)
3. Fill in the required information:
   - **App name**: Resume Generator
   - **User support email**: Your email
   - **Developer contact information**: Your email
4. Add scopes:
   - `openid`
   - `email`
   - `profile`
5. Add test users (your email and any other emails you want to test with)
6. Save and continue

## Step 4: Create OAuth Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Choose "Web application"
4. Configure the settings:
   - **Name**: Resume Generator Web Client
   - **Authorized JavaScript origins**: 
     - `http://localhost:8000` (for local development)
     - `https://yourdomain.com` (for production)
   - **Authorized redirect URIs**:
     - `http://localhost:8000/auth/google/callback` (for local development)
     - `https://yourdomain.com/auth/google/callback` (for production)
5. Click "Create"
6. Copy the **Client ID** and **Client Secret**

## Step 5: Configure Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and add your Google OAuth credentials:
   ```env
   GOOGLE_CLIENT_ID=your-google-client-id-here
   GOOGLE_CLIENT_SECRET=your-google-client-secret-here
   GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
   ```

## Step 6: Install Dependencies

Make sure you have the required OAuth dependencies installed:

```bash
pip install authlib httpx
```

## Step 7: Test the Integration

1. Start your application:
   ```bash
   python app.py
   ```

2. Go to `http://localhost:8000/login`
3. You should see a "Continue with Google" button
4. Click it to test the OAuth flow

## Production Deployment

For production deployment:

1. Update the authorized origins and redirect URIs in Google Cloud Console
2. Update the `GOOGLE_REDIRECT_URI` in your production environment variables
3. Make sure your domain is verified in Google Cloud Console

## Troubleshooting

### Common Issues

1. **"redirect_uri_mismatch" error**:
   - Check that the redirect URI in your Google Cloud Console matches exactly with the one in your environment variables
   - Make sure there are no trailing slashes or typos

2. **"invalid_client" error**:
   - Verify that your Client ID and Client Secret are correct
   - Check that the OAuth consent screen is properly configured

3. **"access_denied" error**:
   - Make sure the user's email is added to test users (for apps in testing mode)
   - Check that required scopes are properly configured

4. **Google OAuth button not showing**:
   - Check browser console for JavaScript errors
   - Verify that the `/api/auth/google/status` endpoint returns `{"available": true, "configured": true}`

### Debug Mode

To debug OAuth issues, check the application logs for detailed error messages. The application will log OAuth initialization status on startup.

## Security Considerations

1. **Never commit your `.env` file** - it contains sensitive credentials
2. **Use HTTPS in production** - OAuth requires secure connections
3. **Regularly rotate your OAuth credentials** - especially if they're compromised
4. **Limit OAuth scopes** - only request the minimum permissions needed
5. **Validate redirect URIs** - ensure they point to your legitimate domains

## Features Enabled by Google OAuth

Once configured, users can:

- Sign in with their Google account
- Skip manual registration
- Have their profile automatically populated with Google account information
- Enjoy a seamless authentication experience

The application will automatically:

- Create user accounts for new Google users
- Link existing accounts if the email matches
- Populate profile pictures from Google accounts
- Mark Google accounts as verified

## Support

If you encounter issues with Google OAuth setup, please check:

1. Google Cloud Console configuration
2. Environment variables
3. Application logs
4. Network connectivity

For additional help, refer to the [Google OAuth 2.0 documentation](https://developers.google.com/identity/protocols/oauth2).