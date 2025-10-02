import psycopg2
import sqlite3
import sys
import os
from decimal import Decimal


def convert_value(val):
    """Convert PostgreSQL values to SQLite-compatible types."""
    if val is None:
        return None
    elif isinstance(val, Decimal):
        # Convert PostgreSQL Decimal to float for SQLite
        return float(val)
    elif isinstance(val, (list, dict)):
        # Convert arrays and JSON to string
        return str(val)
    elif hasattr(val, "isoformat"):
        # Convert datetime objects to string
        return val.isoformat()
    elif isinstance(val, (bytes, bytearray)):
        # Convert binary data to string
        return val.decode("utf-8", errors="replace")
    else:
        return val


def copy_table_data(pg_cur, sqlite_cur, table_name, schema="prod_toxrefdb_3_0"):
    """Copy data from PostgreSQL table to SQLite table."""
    print(f"Converting table: {table_name}")

    # Get table structure
    pg_cur.execute(f"""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_schema = '{schema}' 
        AND table_name = '{table_name}'
        ORDER BY ordinal_position
    """)
    columns = pg_cur.fetchall()

    # Create SQLite table
    col_defs = []
    for col_name, data_type, is_nullable in columns:
        sqlite_type = "TEXT"
        if "int" in data_type.lower():
            sqlite_type = "INTEGER"
        elif any(
            t in data_type.lower() for t in ["numeric", "decimal", "real", "double"]
        ):
            sqlite_type = "REAL"
        elif "bool" in data_type.lower():
            sqlite_type = "INTEGER"

        null_constraint = "" if is_nullable == "YES" else " NOT NULL"
        col_defs.append(f'"{col_name}" {sqlite_type}{null_constraint}')

    create_sql = f'CREATE TABLE "{table_name}" ({", ".join(col_defs)})'
    sqlite_cur.execute(create_sql)

    # Copy data
    pg_cur.execute(f'SELECT * FROM "{schema}"."{table_name}"')
    col_names = [desc[0] for desc in pg_cur.description]
    placeholders = ",".join(["?" for _ in col_names])
    col_names_quoted = ",".join([f'"{col}"' for col in col_names])
    insert_sql = (
        f'INSERT INTO "{table_name}" ({col_names_quoted}) VALUES ({placeholders})'
    )

    # Process data in batches
    batch_size = 1000
    total_rows = 0

    while True:
        rows = pg_cur.fetchmany(batch_size)
        if not rows:
            break

        # Convert all values in the batch
        converted_rows = []
        for row in rows:
            converted_row = tuple(convert_value(val) for val in row)
            converted_rows.append(converted_row)

        # Insert batch
        try:
            sqlite_cur.executemany(insert_sql, converted_rows)
            total_rows += len(converted_rows)
        except Exception as e:
            print(f"    Warning: Batch insert failed ({e}), trying individual rows...")
            # Fallback to individual row insertion
            for i, row in enumerate(converted_rows):
                try:
                    sqlite_cur.execute(insert_sql, row)
                    total_rows += 1
                except Exception as row_e:
                    print(f"    Skipping row {i}: {row_e}")

    print(f"  Copied {total_rows} rows")
    return total_rows


def copy_materialized_views(pg_cur, sqlite_cur, schema="prod_toxrefdb_3_0"):
    """Copy materialized views as regular tables."""
    pg_cur.execute(f"""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = '{schema}' 
        AND table_type = 'VIEW'
        ORDER BY table_name
    """)
    views = pg_cur.fetchall()

    print(f"Found {len(views)} materialized views to convert")

    for (view_name,) in views:
        print(f"Converting materialized view: {view_name}")

        # Get view structure
        pg_cur.execute(f'SELECT * FROM "{schema}"."{view_name}" LIMIT 1')
        if not pg_cur.description:
            continue

        col_names = [desc[0] for desc in pg_cur.description]

        # Create table (all columns as TEXT for simplicity)
        col_defs = [f'"{col}" TEXT' for col in col_names]
        create_sql = f'CREATE TABLE "{view_name}" ({", ".join(col_defs)})'
        sqlite_cur.execute(create_sql)

        # Copy all data
        pg_cur.execute(f'SELECT * FROM "{schema}"."{view_name}"')
        placeholders = ",".join(["?" for _ in col_names])
        col_names_quoted = ",".join([f'"{col}"' for col in col_names])
        insert_sql = (
            f'INSERT INTO "{view_name}" ({col_names_quoted}) VALUES ({placeholders})'
        )

        batch_size = 1000
        total_rows = 0

        while True:
            rows = pg_cur.fetchmany(batch_size)
            if not rows:
                break

            # Convert all values in the batch
            converted_rows = []
            for row in rows:
                converted_row = tuple(convert_value(val) for val in row)
                converted_rows.append(converted_row)

            # Insert batch
            try:
                sqlite_cur.executemany(insert_sql, converted_rows)
                total_rows += len(converted_rows)
            except Exception as e:
                print(
                    f"    Warning: Batch insert failed ({e}), trying individual rows..."
                )
                # Fallback to individual row insertion
                for i, row in enumerate(converted_rows):
                    try:
                        sqlite_cur.execute(insert_sql, row)
                        total_rows += 1
                    except Exception as row_e:
                        print(f"    Skipping row {i}: {row_e}")

        print(f"  Copied {total_rows} rows from materialized view")


def convert_postgres_to_sqlite():
    """Main conversion function."""
    try:
        # Connect to PostgreSQL
        pg_conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="toxrefdb",
            user="postgres",
            password="password",
        )
        pg_cur = pg_conn.cursor()

        # Create SQLite database
        sqlite_path = os.path.join(os.getcwd(), "brick", "toxrefdb.sqlite")
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_cur = sqlite_conn.cursor()

        # Get all base tables
        pg_cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'prod_toxrefdb_3_0' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        tables = pg_cur.fetchall()

        print(f"Found {len(tables)} tables to convert")

        # Convert all base tables
        for (table_name,) in tables:
            copy_table_data(pg_cur, sqlite_cur, table_name)
            sqlite_conn.commit()

        # Convert materialized views
        copy_materialized_views(pg_cur, sqlite_cur)
        sqlite_conn.commit()

        # Close connections
        sqlite_conn.close()
        pg_conn.close()

        print("Conversion completed successfully!")
        return True

    except Exception as e:
        print(f"Error during conversion: {e}")
        return False


if __name__ == "__main__":
    success = convert_postgres_to_sqlite()
    sys.exit(0 if success else 1)
