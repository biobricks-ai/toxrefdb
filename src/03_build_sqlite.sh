mkdir -p brick
[ -f brick/toxrefdb.sqlite ] && rm brick/toxrefdb.sqlite # remove old sqlite file if it exists
src/scripts/mysql2sqlite downloads/mysql_toxrefdb.sql | sqlite3 brick/toxrefdb.sqlite

check_row_count() {
    table=$1
    min_count=$2
    count=$(sqlite3 brick/toxrefdb.sqlite "SELECT COUNT(*) FROM $table;")
    if [ "$count" -lt "$min_count" ]; then
        echo "Table $table has less than $min_count rows. Actual count: $count"
        exit 1
    fi
}

# Perform the checks
check_row_count "chemical" 1000
check_row_count "dose" 1000
check_row_count "dtg" 1000

echo "All checks passed."
exit 0