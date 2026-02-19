#!/bin/bash

# =============================================================================
# Oracle Cloud Free Tier Setup Script for Bet_Hope
# =============================================================================
# Run this script on your Oracle Cloud VM after SSH'ing in:
# ssh ubuntu@<your-server-ip>
# wget -O setup.sh https://raw.githubusercontent.com/Taofeek26/bet_hope/main/scripts/oracle-cloud-setup.sh
# chmod +x setup.sh && sudo ./setup.sh
# =============================================================================

set -e

echo "🚀 Bet_Hope Oracle Cloud Setup"
echo "==============================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root: sudo ./setup.sh"
    exit 1
fi

# Update system
echo "📦 Updating system packages..."
apt-get update && apt-get upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
curl -fsSL https://get.docker.com | sh
usermod -aG docker ubuntu

# Install Docker Compose
echo "📦 Installing Docker Compose..."
apt-get install -y docker-compose-plugin

# Install useful tools
echo "🔧 Installing utilities..."
apt-get install -y git htop nano ufw

# Configure firewall
echo "🔥 Configuring firewall..."
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw --force enable

# Create app directory
echo "📁 Setting up application directory..."
mkdir -p /opt/bet_hope
chown ubuntu:ubuntu /opt/bet_hope

# Clone repository
echo "📥 Cloning repository..."
cd /opt/bet_hope
sudo -u ubuntu git clone https://github.com/Taofeek26/bet_hope.git .

# Create production environment file
echo "⚙️  Creating environment configuration..."
cat > /opt/bet_hope/backend/.env.prod << 'ENVFILE'
# =============================================================================
# BET_HOPE PRODUCTION ENVIRONMENT
# =============================================================================
# IMPORTANT: Update these values!

DJANGO_SECRET_KEY=CHANGE_THIS_TO_A_SECURE_KEY
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=YOUR_SERVER_IP,localhost
DJANGO_ENV=production

# Database password (also update in docker-compose if changed)
DB_PASSWORD=secure_bet_hope_password_2024

# Redis / Celery
CELERY_RESULT_BACKEND=django-db

# API Keys - UPDATE THESE!
API_FOOTBALL_KEY=YOUR_API_FOOTBALL_KEY
OPENAI_API_KEY=YOUR_OPENAI_KEY

# CORS
CORS_ALLOWED_ORIGINS=http://YOUR_SERVER_IP,http://localhost

# Features
ENABLE_DOCUMENT_AI=True
ENVFILE

chown ubuntu:ubuntu /opt/bet_hope/backend/.env.prod

# Generate Django secret key
DJANGO_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')
sed -i "s/CHANGE_THIS_TO_A_SECURE_KEY/$DJANGO_KEY/" /opt/bet_hope/backend/.env.prod

# Create swap file (important for 1GB RAM servers)
echo "💾 Creating swap file for better performance..."
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# Set permissions
chown -R ubuntu:ubuntu /opt/bet_hope

echo ""
echo "✅ Setup complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "NEXT STEPS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Edit the environment file with your API keys:"
echo "   nano /opt/bet_hope/backend/.env.prod"
echo ""
echo "2. Update DJANGO_ALLOWED_HOSTS and CORS_ALLOWED_ORIGINS"
echo "   with your server's public IP address"
echo ""
echo "3. Log out and back in (for Docker permissions):"
echo "   exit"
echo "   ssh ubuntu@<your-server-ip>"
echo ""
echo "4. Start the application:"
echo "   cd /opt/bet_hope"
echo "   ./deploy.sh start"
echo ""
echo "5. Create admin user:"
echo "   ./deploy.sh createsuperuser"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
