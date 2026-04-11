"""
DB Migration: Add image_url to complaints, create comments table if missing
"""
import sqlite3, os

db_path = os.path.join(os.path.dirname(__file__), "civic.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Check complaints columns
cur.execute("PRAGMA table_info(complaints)")
cols = [row[1] for row in cur.fetchall()]
print("Complaints columns:", cols)

if "image_url" not in cols:
    cur.execute("ALTER TABLE complaints ADD COLUMN image_url TEXT")
    print("✅ Added image_url column to complaints")
else:
    print("ℹ️  image_url already exists")

# Create comments table if it doesn't exist
cur.execute("""
CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    complaint_id TEXT NOT NULL,
    user_email TEXT NOT NULL,
    user_name TEXT NOT NULL,
    text TEXT NOT NULL,
    timestamp DATETIME
)
""")
print("✅ Comments table ready")

conn.commit()
conn.close()
print("✅ Migration complete")
