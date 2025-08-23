# Production Deployment Guide - Resume Generator Pro

## 🚀 Complete Production-Ready Stripe Payment Integration

This guide covers deploying the Resume Generator application with full Stripe payment integration alongside cryptocurrency payments.

## 📋 Prerequisites

- Python 3.8+
- Node.js (for frontend dependencies)
- PostgreSQL (recommended for production)
- Stripe Account (for payment processing)
- Domain name and SSL certificate
- Server with at least 2GB RAM

## 🔧 Environment Configuration

### 1. Stripe Setup

1. **Create Stripe Account**: Go to [stripe.com](https://stripe.com) and create an account
2. **Get API Keys**: 
   - Navigate to Developers > API keys
   - Copy your Publishable key (pk_live_...) and Secret key (sk_live_...)
3. **Setup Webhooks**:
   - Go to Developers > Webhooks
   - Add endpoint: `https://yourdomain.com/api/stripe/webhook`
   - Select events: `payment_intent.succeeded`, `payment_intent.payment_failed`, `payment_intent.canceled`
   - Copy the webhook secret (whsec_...)

### 2. Environment Variables

Update your `.env` file with production values:

```bash
# OpenRouter API Configuration
OPENROUTER_API_KEY=sk-or-v1-your-actual-openrouter-key
OPENROUTER_MODEL=anthropic/claude-3-haiku
OPENROUTER_APP_NAME=Resume-Generator-Pro
OPENROUTER_APP_URL=https://yourdomain.com

# Application Configuration
SECRET_KEY=your-super-secure-secret-key-here-min-32-chars
ENVIRONMENT=production
DEBUG=false

# Stripe Payment Configuration (PRODUCTION)
STRIPE_SECRET_KEY=sk_live_your_actual_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_actual_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_actual_webhook_secret

# Business Information
BUSINESS_NAME=Resume Generator Pro
BUSINESS_URL=https://yourdomain.com
SUPPORT_EMAIL=support@yourdomain.com

# Cryptocurrency Payment Configuration
USDT_TRC20_WALLET=your-actual-usdt-trc20-wallet-address
CREDIT_PRICE_USD=0.50

# Database Configuration (PostgreSQL recommended)
DATABASE_URL=postgresql://username:password@localhost:5432/resume_generator

# Security Settings
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
SESSION_TIMEOUT_HOURS=24
MAX_UPLOAD_SIZE_MB=10

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/var/log/resume-generator/app.log
```

## 🏗️ Installation Steps

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3.8 python3.8-venv python3.8-dev python-is-python3 -y
sudo apt install postgresql postgresql-contrib nginx certbot python3-certbot-nginx -y

# Create application user
sudo useradd -m -s /bin/bash resumegen
sudo usermod -aG sudo resumegen
```

### 2. Application Deployment

```bash
# Switch to application user
sudo su - resumegen

# Clone repository
git clone https://github.com/yourusername/resume-generator.git
cd resume-generator

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your production values
nano .env
```

### 3. Database Setup

```bash
# Create PostgreSQL database
sudo -u postgres createdb resume_generator
sudo -u postgres createuser resumegen
sudo -u postgres psql -c "ALTER USER resumegen PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE resume_generator TO resumegen;"

# Run database migrations
python -c "from models import create_tables; create_tables()"
```

### 4. Test Stripe Integration

```bash
# Run comprehensive tests
python test_stripe_payments.py

# Test with real Stripe keys (use test mode first)
python -c "
from stripe_payment import StripePaymentService
from models import get_db
service = StripePaymentService()
db = next(get_db())
plans = service.get_pricing_plans(db)
print('Stripe integration working:', len(plans) > 0)
"
```

## 🌐 Web Server Configuration

### 1. Nginx Configuration

Create `/etc/nginx/sites-available/resume-generator`:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/login {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        alias /home/resumegen/resume-generator/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # File uploads
    client_max_body_size 10M;
}
```

### 2. SSL Certificate

```bash
# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Enable nginx site
sudo ln -s /etc/nginx/sites-available/resume-generator /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 🔄 Process Management

### 1. Systemd Service

Create `/etc/systemd/system/resume-generator.service`:

```ini
[Unit]
Description=Resume Generator FastAPI Application
After=network.target

[Service]
Type=simple
User=resumegen
Group=resumegen
WorkingDirectory=/home/resumegen/resume-generator
Environment=PATH=/home/resumegen/resume-generator/venv/bin
ExecStart=/home/resumegen/resume-generator/venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000 --workers 4
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/resumegen/resume-generator

[Install]
WantedBy=multi-user.target
```

### 2. Start Services

```bash
# Enable and start application
sudo systemctl daemon-reload
sudo systemctl enable resume-generator
sudo systemctl start resume-generator

# Check status
sudo systemctl status resume-generator
```

## 💳 Payment Testing

### 1. Stripe Test Cards

Use these test cards in Stripe test mode:

- **Successful payment**: `4242424242424242`
- **Declined payment**: `4000000000000002`
- **Requires authentication**: `4000002500003155`

### 2. Test Payment Flow

1. Navigate to `/pricing`
2. Select "Credit/Debit Card" payment method
3. Choose a plan and click "Pay with Card"
4. Use test card: `4242424242424242`
5. Verify credits are added to account

### 3. Webhook Testing

```bash
# Install Stripe CLI for webhook testing
curl -s https://packages.stripe.com/api/security/keypair/stripe-cli-gpg/public | gpg --dearmor | sudo tee /usr/share/keyrings/stripe.gpg
echo "deb [signed-by=/usr/share/keyrings/stripe.gpg] https://packages.stripe.com/stripe-cli-debian-local stable main" | sudo tee -a /etc/apt/sources.list.d/stripe.list
sudo apt update && sudo apt install stripe

# Test webhooks locally
stripe listen --forward-to localhost:8000/api/stripe/webhook
```

## 📊 Monitoring & Logging

### 1. Application Logs

```bash
# View application logs
sudo journalctl -u resume-generator -f

# View nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 2. Health Checks

Create monitoring script `/home/resumegen/health-check.sh`:

```bash
#!/bin/bash
# Health check script

# Check application
if curl -f http://localhost:8000/api/payment-methods > /dev/null 2>&1; then
    echo "✅ Application healthy"
else
    echo "❌ Application unhealthy"
    sudo systemctl restart resume-generator
fi

# Check database
if python -c "from models import get_db; next(get_db())" > /dev/null 2>&1; then
    echo "✅ Database healthy"
else
    echo "❌ Database connection failed"
fi
```

### 3. Backup Strategy

```bash
# Database backup script
#!/bin/bash
BACKUP_DIR="/home/resumegen/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
pg_dump resume_generator > $BACKUP_DIR/db_backup_$DATE.sql

# Keep only last 7 days
find $BACKUP_DIR -name "db_backup_*.sql" -mtime +7 -delete
```

## 🔒 Security Checklist

- [ ] SSL certificate installed and auto-renewal configured
- [ ] Environment variables secured (no secrets in code)
- [ ] Database credentials rotated
- [ ] Stripe webhook endpoints secured
- [ ] Rate limiting configured
- [ ] Security headers added
- [ ] File upload restrictions in place
- [ ] Regular security updates scheduled
- [ ] Backup strategy implemented
- [ ] Monitoring and alerting configured

## 🚀 Go Live Checklist

1. **Pre-Launch**:
   - [ ] All tests passing (crypto + Stripe)
   - [ ] Environment variables configured
   - [ ] SSL certificate active
   - [ ] Database migrations complete
   - [ ] Backup strategy tested

2. **Launch**:
   - [ ] Switch Stripe to live mode
   - [ ] Update webhook URLs to production
   - [ ] Test payment flows with real cards
   - [ ] Monitor logs for errors
   - [ ] Verify email notifications working

3. **Post-Launch**:
   - [ ] Monitor payment success rates
   - [ ] Check webhook delivery
   - [ ] Verify credit additions
   - [ ] Monitor application performance
   - [ ] Set up alerting for failures

## 📞 Support & Maintenance

### Common Issues

1. **Stripe webhook failures**: Check webhook URL and secret
2. **Payment not completing**: Verify Stripe keys and webhook events
3. **Credits not added**: Check webhook processing and database logs
4. **SSL issues**: Verify certificate renewal

### Maintenance Tasks

- Weekly: Check logs and payment success rates
- Monthly: Update dependencies and security patches
- Quarterly: Review and rotate secrets
- Annually: Renew SSL certificates (if not auto-renewed)

## 🎯 Performance Optimization

1. **Database**: Use connection pooling and query optimization
2. **Caching**: Implement Redis for session and pricing plan caching
3. **CDN**: Use CloudFlare or similar for static assets
4. **Monitoring**: Set up APM tools like New Relic or DataDog

---

**🎊 Congratulations!** Your Resume Generator Pro is now production-ready with dual payment options (Stripe + Cryptocurrency), comprehensive security, and enterprise-grade infrastructure.

For support, contact: support@yourdomain.com