def run_migration(conn):
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(game_list);")
    columns = [row[1] for row in cursor.fetchall()]

    if "playcount_offset" not in columns:
        print("Applying migration: Add playcount_offset")
        cursor.execute("ALTER TABLE game_list ADD COLUMN playcount_offset INTEGER DEFAULT 0;")
        conn.commit()
    else:
        print("Migration skipped: playcount_offset already exists")