#!/bin/bash

# Create a directory for the SQLite file
mkdir -p brick

# Remove the old SQLite file if it exists
[ -f brick/toxrefdb.sqlite ] && rm brick/toxrefdb.sqlite

# Check if required tools are installed
echo "Checking for required tools..."

# Install SQLite3 if not present
if ! command -v sqlite3 &> /dev/null; then
    echo "Installing sqlite3..."
    sudo apt-get update && sudo apt-get install -y sqlite3
fi

# Install PostgreSQL client tools if not present
if ! command -v pg_restore &> /dev/null; then
    echo "Installing postgresql-client..."
    sudo apt-get update && sudo apt-get install -y postgresql-client
fi

# Install Python packages for PostgreSQL to SQLite conversion
echo "Installing Python packages for conversion..."
pip install psycopg2-binary

# Start a temporary PostgreSQL container
echo "Starting temporary PostgreSQL container..."
docker rm -f temp_postgres 2> /dev/null
docker run -d --name temp_postgres \
    -e POSTGRES_DB=toxrefdb \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=password \
    -p 5432:5432 \
    postgres:13

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
timeout=60
elapsed=0
while ! docker exec temp_postgres pg_isready -U postgres && [ $elapsed -lt $timeout ]; do
    echo "Waiting for PostgreSQL... ($elapsed seconds)"
    sleep 5
    elapsed=$((elapsed + 5))
done

if [ $elapsed -ge $timeout ]; then
    echo "PostgreSQL failed to start within timeout"
    docker rm -f temp_postgres
    exit 1
fi

# Restore the dump file to PostgreSQL
echo "Restoring PostgreSQL dump to temporary database..."
docker exec -i temp_postgres pg_restore -U postgres -d toxrefdb -v --no-owner --no-privileges < download/toxrefdb.dump

# Check if the restore was successful (ignore warnings about missing users)
if docker exec temp_postgres psql -U postgres -d toxrefdb -c "\dt prod_toxrefdb_3_0.*" | grep -q "prod_toxrefdb_3_0"; then
    echo "PostgreSQL dump restored successfully (ignoring ownership warnings)"
else
    echo "Failed to restore PostgreSQL dump - no tables found"
    docker rm -f temp_postgres
    exit 1
fi

# Convert PostgreSQL database to SQLite using Python
echo "Converting PostgreSQL database to SQLite..."
uv run python3 src/scripts/pg_to_sqlite.py

if [ $? -eq 0 ]; then
    echo "Successfully converted PostgreSQL database to SQLite!"
    echo "SQLite database created at: brick/toxrefdb.sqlite"
else
    echo "Failed to convert database using Python script"
    rm -f /tmp/pg_to_sqlite.py
    docker rm -f temp_postgres
    exit 1
fi

# Cleanup
echo "Cleaning up..."
docker rm -f temp_postgres

echo "Conversion completed successfully!"