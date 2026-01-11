"""
Clear oracle app migration records from database
Run with: python3 manage.py shell < clear_oracle_migrations.py
"""
from django.db import connection

print("Clearing oracle migration records...")
with connection.cursor() as cursor:
    cursor.execute("DELETE FROM django_migrations WHERE app = 'oracle';")
    deleted = cursor.rowcount
    connection.commit()
print(f"✓ Deleted {deleted} oracle migration record(s)")
print("\nNext step: Run 'python3 manage.py migrate oracle --fake' to re-record migrations")
