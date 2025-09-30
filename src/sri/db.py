import psycopg2
import psycopg2.extras

def get_conn(database_url: str):
    return psycopg2.connect(database_url)

def execute(conn, sql, params=None):
    with conn, conn.cursor() as cur:
        cur.execute(sql, params or ())

def fetchone(conn, sql, params=None):
    with conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()

def fetchall(conn, sql, params=None):
    with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()
