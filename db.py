import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db(dens_config=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS beddings ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "owner_name TEXT, "
        "is_nest INTEGER NOT NULL DEFAULT 0, "
        "condition INTEGER NOT NULL DEFAULT 100)"
    )
    try:
        c.execute("ALTER TABLE beddings ADD COLUMN is_nest INTEGER NOT NULL DEFAULT 0")
    except Exception:
        pass
    c.execute(
        "CREATE TABLE IF NOT EXISTS walls ("
        "id INTEGER PRIMARY KEY, "
        "condition INTEGER NOT NULL DEFAULT 78)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS dens ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "den_key TEXT NOT NULL UNIQUE, "
        "den_name TEXT NOT NULL, "
        "structure TEXT NOT NULL, "
        "condition INTEGER NOT NULL DEFAULT 100, "
        "preset_condition INTEGER NOT NULL DEFAULT 100)"
    )
    try:
        c.execute("ALTER TABLE dens ADD COLUMN preset_condition INTEGER NOT NULL DEFAULT 100")
    except Exception:
        pass
    c.execute("SELECT COUNT(*) FROM walls")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO walls (id, condition) VALUES (1, 78)")
    if dens_config:
        for den in dens_config:
            preset = den.get("preset", 100)
            c.execute(
                "INSERT INTO dens (den_key, den_name, structure, condition, preset_condition) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(den_key) DO UPDATE SET "
                "den_name=excluded.den_name, structure=excluded.structure, "
                "preset_condition=excluded.preset_condition",
                (den["key"], den["name"], den["structure"], preset, preset)
            )
    conn.commit()
    conn.close()


def get_walls_condition():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT condition FROM walls WHERE id=1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0


def set_walls_condition(value):
    value = max(0, min(100, value))
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE walls SET condition=? WHERE id=1", (value,))
    conn.commit()
    conn.close()
    return value


def get_all_dens():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT den_key, den_name, structure, condition FROM dens ORDER BY id")
    rows = c.fetchall()
    conn.close()
    return [{"key": r[0], "name": r[1], "structure": r[2], "condition": r[3]} for r in rows]


def set_den_condition(den_key, value):
    value = max(0, min(100, value))
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE dens SET condition=? WHERE den_key=?", (value, den_key))
    conn.commit()
    conn.close()
    return value


def get_all_beddings():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, owner_name, is_nest, condition FROM beddings ORDER BY id")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "owner": r[1], "is_nest": bool(r[2]), "condition": r[3]} for r in rows]


def get_bedding_by_id(bedding_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, owner_name, is_nest, condition FROM beddings WHERE id=?", (bedding_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "owner": row[1], "is_nest": bool(row[2]), "condition": row[3]}
    return None


def add_bedding(owner_name):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO beddings (owner_name, is_nest, condition) VALUES (?, 0, 100)", (owner_name,))
    bid = c.lastrowid
    conn.commit()
    conn.close()
    return bid


def add_nest():
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO beddings (owner_name, is_nest, condition) VALUES (NULL, 1, 100)")
    nid = c.lastrowid
    conn.commit()
    conn.close()
    return nid


def shake_bedding(bedding_id, amount):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT condition FROM beddings WHERE id=?", (bedding_id,))
    row = c.fetchone()
    if row is None:
        conn.close()
        return None
    new_val = min(100, row[0] + amount)
    c.execute("UPDATE beddings SET condition=? WHERE id=?", (new_val, bedding_id))
    conn.commit()
    conn.close()
    return new_val


def rename_bedding(bedding_id, new_owner):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT owner_name FROM beddings WHERE id=? AND is_nest=0", (bedding_id,))
    row = c.fetchone()
    if row is None:
        conn.close()
        return None
    old_owner = row[0]
    c.execute("UPDATE beddings SET owner_name=? WHERE id=?", (new_owner, bedding_id))
    conn.commit()
    conn.close()
    return old_owner


def delete_bedding(bedding_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT condition, is_nest FROM beddings WHERE id=?", (bedding_id,))
    row = c.fetchone()
    if row:
        c.execute("DELETE FROM beddings WHERE id=?", (bedding_id,))
        conn.commit()
        conn.close()
        return {"condition": row[0], "is_nest": bool(row[1])}
    conn.close()
    return None


def wear_all_beddings(decay):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE beddings SET condition = MAX(0, condition - ?)", (decay,))
    conn.commit()
    conn.close()

    
def set_bedding_condition(bedding_id, value):
    value = max(0, min(100, value))
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE beddings SET condition=? WHERE id=?", (value, bedding_id))
    conn.commit()
    conn.close()
    return value


def lower_all_beddings(amount):
    amount = max(0, amount)
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE beddings SET condition = MAX(0, condition - ?)", (amount,))
    conn.commit()
    conn.close()


def lower_walls(amount):
    amount = max(0, amount)
    current = get_walls_condition()
    return set_walls_condition(current - amount)


def lower_all_dens(amount):
    amount = max(0, amount)
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE dens SET condition = MAX(0, condition - ?)", (amount,))
    conn.commit()
    conn.close()
