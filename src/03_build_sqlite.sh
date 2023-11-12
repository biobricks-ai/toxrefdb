# Create a directory for the SQLite file
mkdir -p brick

# Remove the old SQLite file if it exists
[ -f brick/toxrefdb.sqlite ] && rm brick/toxrefdb.sqlite

# Remove the docker container `mysql_toxrefdb` if it exists
docker rm -f mysql_toxrefdb 2> /dev/null

# Remove the docker image `mysql_toxrefdb` if it exists
docker rmi -f mysql_toxrefdb 2> /dev/null

# Build the docker image
docker build -t mysql_toxrefdb -f src/scripts/Dockerfile .

# Run the docker container
docker run -d -p 3306:3306 --name mysql_toxrefdb mysql_toxrefdb

# Wait for the initialization log file to confirm readiness
echo "Waiting for database initialization to complete..."
until docker exec mysql_toxrefdb test -f /tmp/db-init.log; do
    echo -n "."; sleep 3;
done
sleep 30;
echo "Database initialization confirmed by log file."

# create sqlite database
pip install mysql-to-sqlite3

# Attempt to create SQLite database for up to 5 minutes
timeout=300  # 3 minutes in seconds
elapsed=0
echo "Attempting to create SQLite database..."
while ! mysql2sqlite -f brick/toxrefdb.sqlite -d toxrefdb -u root --mysql-password password && [ $elapsed -lt $timeout ]; do
    echo "Retrying in 10 seconds..."
    sleep 10
    elapsed=$((elapsed + 10))
done

# Remove the docker container `mysql_toxrefdb`
docker rm -f mysql_toxrefdb

# Remove the docker image `mysql_toxrefdb`
docker rmi mysql_toxrefdb