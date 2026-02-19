#!/bin/bash
set -e

# Default site name if not provided
SITE_NAME=${SITE_NAME:-platform.rokct.ai}

# Function to setup the site
setup_site() {
    echo "Checking site configuration..."
    
    if [ ! -d "sites/$SITE_NAME" ]; then
        echo "🔥 Site '$SITE_NAME' not found. Starting Fresh Install..."

        # Check for Golden Seed
        if [ -f "apps/seed_data/seed.sql.gz" ]; then
            echo "✨ Golden Seed Found! restoring from CI Artifact..."
            # Create new site using the seed (Fast Boot)
            # We use --force to overwrite if partial artifacts exist
            # We set admin password to 'admin' (Change immediately in prod!)
            bench new-site "$SITE_NAME" \
                --source-sql "apps/seed_data/seed.sql.gz" \
                --admin-password "${ADMIN_PASSWORD:-admin}" \
                --db-root-password "${DB_ROOT_PASSWORD:-admin}" \
                --install-app rpanel \
                --force
            
            echo "✅ Site restored from Golden Seed."
        else
            echo "⚠️ No Golden Seed found. Doing standard clean install..."
            bench new-site "$SITE_NAME" \
                --admin-password "${ADMIN_PASSWORD:-admin}" \
                --db-root-password "${DB_ROOT_PASSWORD:-admin}" \
                --install-app rpanel
        fi
        
        # Set as current site
        bench use "$SITE_NAME"
    else
        echo "✅ Site '$SITE_NAME' already exists. Skipping install."
    fi
}

# Run setup if we are the main command
if [ "$1" = "bench" ] && [ "$2" = "start" ]; then
    setup_site
fi

# Exec the passed command (usually 'bench start')
exec "$@"
