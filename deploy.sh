#!/bin/bash

# =============================================================================
# Bet_Hope Production Deployment Script
# =============================================================================

set -e  # Exit on error

echo "🚀 Bet_Hope Deployment Script"
echo "=============================="

# Check if .env.prod exists
if [ ! -f "backend/.env.prod" ]; then
    echo "❌ Error: backend/.env.prod not found!"
    echo "   Copy backend/.env.prod.example to backend/.env.prod and configure it."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed!"
    echo "   Install with: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# Parse command
case "$1" in
    start)
        echo "📦 Building and starting services..."
        docker compose -f docker-compose.prod.yml up -d --build
        echo "⏳ Waiting for database to be ready..."
        sleep 10
        echo "🗄️  Running migrations..."
        docker compose -f docker-compose.prod.yml exec -T backend python manage.py migrate --noinput
        echo "📁 Collecting static files..."
        docker compose -f docker-compose.prod.yml exec -T backend python manage.py collectstatic --noinput
        echo "✅ Deployment complete!"
        echo "   Access your app at http://localhost (or your domain)"
        ;;

    stop)
        echo "🛑 Stopping services..."
        docker compose -f docker-compose.prod.yml down
        echo "✅ Services stopped."
        ;;

    restart)
        echo "🔄 Restarting services..."
        docker compose -f docker-compose.prod.yml restart
        echo "✅ Services restarted."
        ;;

    logs)
        docker compose -f docker-compose.prod.yml logs -f ${2:-}
        ;;

    update)
        echo "📥 Pulling latest changes..."
        git pull origin main
        echo "🔄 Rebuilding and restarting..."
        docker compose -f docker-compose.prod.yml up -d --build
        echo "🗄️  Running migrations..."
        docker compose -f docker-compose.prod.yml exec -T backend python manage.py migrate --noinput
        echo "✅ Update complete!"
        ;;

    shell)
        echo "🐚 Opening Django shell..."
        docker compose -f docker-compose.prod.yml exec backend python manage.py shell
        ;;

    createsuperuser)
        echo "👤 Creating superuser..."
        docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
        ;;

    backup)
        echo "💾 Creating database backup..."
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        docker compose -f docker-compose.prod.yml exec -T db pg_dump -U bet_hope bet_hope > "backup_${TIMESTAMP}.sql"
        echo "✅ Backup saved to backup_${TIMESTAMP}.sql"
        ;;

    status)
        docker compose -f docker-compose.prod.yml ps
        ;;

    *)
        echo "Usage: ./deploy.sh {start|stop|restart|logs|update|shell|createsuperuser|backup|status}"
        echo ""
        echo "Commands:"
        echo "  start           - Build and start all services"
        echo "  stop            - Stop all services"
        echo "  restart         - Restart all services"
        echo "  logs [service]  - View logs (optionally for specific service)"
        echo "  update          - Pull latest code and redeploy"
        echo "  shell           - Open Django shell"
        echo "  createsuperuser - Create admin user"
        echo "  backup          - Backup database"
        echo "  status          - Show service status"
        exit 1
        ;;
esac
