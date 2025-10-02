# docker build -t mysql_toxrefdb .
# docker run -d -p 3306:3306 --name mysql_toxrefdb mysql_toxrefdb
# Use the official MySQL image as the base image
FROM mysql:8.0.35-debian

# Set environment variables for MySQL
ENV MYSQL_DATABASE=toxrefdb
ENV MYSQL_ROOT_PASSWORD=password

# Add execution scripts (executed in alphabetical order)

## Add the SQL script
ADD download/mysql_toxrefdb.sql /docker-entrypoint-initdb.d/01_mysql.sql

## Add database initialization indicator script
ADD src/scripts/init-db.sh /docker-entrypoint-initdb.d/02_init-db.sh
