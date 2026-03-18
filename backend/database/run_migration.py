"""
Database Migration Runner
Run this script to apply database migrations
"""
import os
import sys
import re
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database.connection import Database
from backend.config import settings


def read_sql_file(file_path: str) -> str:
    """Read SQL file content"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def split_sql_statements(sql_content: str) -> list:
    """
    Split SQL content into individual statements
    Handles DELIMITER changes for stored procedures
    """
    statements = []
    current_statement = []
    delimiter = ';'
    in_delimiter_block = False

    lines = sql_content.split('\n')

    for line in lines:
        stripped = line.strip()

        # Handle DELIMITER changes
        if stripped.upper().startswith('DELIMITER'):
            parts = stripped.split(None, 1)
            if len(parts) > 1:
                new_delimiter = parts[1].strip()
                if current_statement:
                    stmt = '\n'.join(current_statement).strip()
                    if stmt:
                        statements.append((stmt, delimiter))
                    current_statement = []
                delimiter = new_delimiter
                in_delimiter_block = delimiter != ';'
                continue

        current_statement.append(line)

        # Check if statement ends with current delimiter
        if stripped.endswith(delimiter):
            stmt = '\n'.join(current_statement).strip()
            if stmt and not stmt.upper().startswith('DELIMITER'):
                # Remove trailing delimiter for execution
                if stmt.endswith(delimiter):
                    stmt = stmt[:-len(delimiter)].strip()
                if stmt:
                    statements.append((stmt, delimiter if delimiter != ';' else ';'))
            current_statement = []

    # Handle remaining content
    if current_statement:
        stmt = '\n'.join(current_statement).strip()
        if stmt:
            if stmt.endswith(delimiter):
                stmt = stmt[:-len(delimiter)].strip()
            if stmt:
                statements.append((stmt, delimiter))

    return statements


def run_migration(migration_file: str, dry_run: bool = False):
    """
    Run a SQL migration file

    Args:
        migration_file: Path to the SQL file
        dry_run: If True, only print statements without executing
    """
    print(f"🚀 Running migration: {migration_file}")
    print(f"📊 Database: {settings.db_name_to_use or 'default'}")
    print("-" * 60)

    # Read SQL file
    sql_content = read_sql_file(migration_file)

    # Split into statements
    statements = split_sql_statements(sql_content)

    print(f"📝 Found {len(statements)} statements to execute\n")

    if dry_run:
        print("🔍 DRY RUN - Statements that would be executed:")
        print("=" * 60)
        for i, (stmt, delim) in enumerate(statements, 1):
            # Skip comments and empty statements
            if stmt.startswith('--') or stmt.startswith('/*') or not stmt.strip():
                continue
            print(f"\n--- Statement {i} ---")
            print(stmt[:500] + "..." if len(stmt) > 500 else stmt)
        return

    # Connect to database
    db = Database(db_name=settings.db_name_to_use)

    success_count = 0
    error_count = 0

    for i, (stmt, delim) in enumerate(statements, 1):
        # Skip comments and empty statements
        if stmt.startswith('--') or stmt.startswith('/*') or not stmt.strip():
            continue

        # Skip SELECT statements (usually for display)
        if stmt.strip().upper().startswith('SELECT'):
            try:
                result = db.execute_query(stmt)
                if result:
                    print(f"✅ Query {i}: {len(result)} rows returned")
                    if len(result) <= 5:
                        for row in result:
                            print(f"   {row}")
            except Exception as e:
                print(f"⚠️ Query {i} (SELECT): {e}")
            continue

        # Execute DDL/DML statements
        try:
            # For stored procedures, we need to handle them specially
            if 'CREATE PROCEDURE' in stmt.upper() or 'CREATE DEFINER' in stmt.upper():
                # Execute as a single block
                with db.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(stmt)
                        conn.commit()
                print(f"✅ Statement {i}: Stored procedure created/updated")
            elif 'ALTER TABLE' in stmt.upper():
                # ALTER TABLE statements
                affected = db.execute_update(stmt)
                print(f"✅ Statement {i}: ALTER TABLE executed ({affected} rows affected)")
            elif 'CREATE TABLE' in stmt.upper():
                affected = db.execute_update(stmt)
                print(f"✅ Statement {i}: CREATE TABLE executed")
            elif 'DROP' in stmt.upper():
                affected = db.execute_update(stmt)
                print(f"✅ Statement {i}: DROP executed")
            else:
                affected = db.execute_update(stmt)
                print(f"✅ Statement {i}: Executed ({affected} rows affected)")

            success_count += 1

        except Exception as e:
            error_msg = str(e)
            # Check if it's a "column already exists" type error (which is OK)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print(f"⚠️ Statement {i}: Skipped (already exists) - {error_msg[:100]}")
            else:
                print(f"❌ Statement {i} failed: {error_msg[:200]}")
                error_count += 1

    print("\n" + "=" * 60)
    print(f"📊 Migration Summary:")
    print(f"   ✅ Successful: {success_count}")
    print(f"   ❌ Failed: {error_count}")
    print("=" * 60)


def check_table_structure():
    """Check the current table structure"""
    print("\n🔍 Checking table structure...")
    print("-" * 60)

    db = Database(db_name=settings.db_name_to_use)

    # Check if table exists
    check_query = """
        SELECT COLUMN_NAME, DATA_TYPE, COLUMN_COMMENT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'target_buyers_precomputed'
        ORDER BY ORDINAL_POSITION
    """

    try:
        columns = db.execute_query(check_query)

        if not columns:
            print("❌ Table 'target_buyers_precomputed' does not exist!")
            return False

        print(f"📋 Table has {len(columns)} columns:\n")

        # Check for new RFM columns
        rfm_columns = ['rfm_recency_score', 'rfm_frequency_score', 'rfm_monetary_score',
                       'rfm_segment', 'sentiment_label', 'sentiment_score',
                       'dominant_intent', 'follow_priority']

        found_rfm = []
        for col in columns:
            col_name = col.get('COLUMN_NAME', '')
            if col_name in rfm_columns:
                found_rfm.append(col_name)
                print(f"   ✅ {col_name} ({col.get('DATA_TYPE')}) - {col.get('COLUMN_COMMENT', '')}")

        print(f"\n📊 RFM columns found: {len(found_rfm)}/{len(rfm_columns)}")

        if len(found_rfm) < len(rfm_columns):
            missing = set(rfm_columns) - set(found_rfm)
            print(f"⚠️ Missing columns: {missing}")
            return False

        return True

    except Exception as e:
        print(f"❌ Error checking table: {e}")
        return False


def test_rfm_calculation():
    """Test RFM calculation on sample data"""
    print("\n🧪 Testing RFM calculation...")
    print("-" * 60)

    db = Database(db_name=settings.db_name_to_use)

    # Check RFM distribution
    query = """
        SELECT
            rfm_segment,
            COUNT(*) as count,
            ROUND(AVG(rfm_recency_score), 2) as avg_r,
            ROUND(AVG(rfm_frequency_score), 2) as avg_f,
            ROUND(AVG(rfm_monetary_score), 2) as avg_m,
            ROUND(AVG(historical_net_sales), 2) as avg_netsales
        FROM target_buyers_precomputed
        WHERE rfm_segment IS NOT NULL
        GROUP BY rfm_segment
        ORDER BY count DESC
    """

    try:
        results = db.execute_query(query)

        if not results:
            print("⚠️ No RFM data found. Run CALL calculate_rfm_scores() first.")
            return False

        print("📊 RFM Segment Distribution:\n")
        for row in results:
            print(f"   {row.get('rfm_segment', 'N/A'):15} | Count: {row.get('count', 0):5} | "
                  f"R: {row.get('avg_r', 0)} F: {row.get('avg_f', 0)} M: {row.get('avg_m', 0)} | "
                  f"Avg NetSales: ¥{row.get('avg_netsales', 0):,.0f}")

        return True

    except Exception as e:
        print(f"❌ Error testing RFM: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Run database migrations')
    parser.add_argument('--dry-run', action='store_true', help='Only print statements without executing')
    parser.add_argument('--check', action='store_true', help='Check table structure')
    parser.add_argument('--test', action='store_true', help='Test RFM calculation')
    parser.add_argument('--file', type=str, help='Path to migration file')

    args = parser.parse_args()

    if args.check:
        check_table_structure()
    elif args.test:
        test_rfm_calculation()
    elif args.file:
        run_migration(args.file, dry_run=args.dry_run)
    else:
        # Default: run the RFM migration
        migration_path = Path(__file__).parent / 'sql' / 'add_rfm_sentiment_fields.sql'
        if migration_path.exists():
            run_migration(str(migration_path), dry_run=args.dry_run)
        else:
            print(f"❌ Migration file not found: {migration_path}")
            print("\nUsage:")
            print("  python run_migration.py --dry-run    # Preview migration")
            print("  python run_migration.py              # Run migration")
            print("  python run_migration.py --check      # Check table structure")
            print("  python run_migration.py --test       # Test RFM calculation")
