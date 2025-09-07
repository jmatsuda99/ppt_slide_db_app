
import sqlite3, os, json, datetime, re, unicodedata

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "slide_db.sqlite")

def _normalize(s: str) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.lower()
    s = re.sub(r"[\s\u3000]+", " ", s)
    return s.strip()

def _split_terms(q: str):
    q = _normalize(q or "")
    q = re.sub(r"[，、,;/]+", " ", q)
    q = re.sub(r"[\s\u3000]+", " ", q)
    terms = [t for t in q.split(" ") if t]
    return terms

def ensure_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        sql = open(os.path.join(os.path.dirname(__file__), "schema.sql"), "r", encoding="utf-8").read()
        conn.executescript(sql)

def get_conn():
    ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def insert_presentation(filename, original_path):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO presentations(filename, original_path, uploaded_at) VALUES(?,?,?)",
            (filename, original_path, datetime.datetime.utcnow().isoformat())
        )
        return cur.lastrowid

def insert_slide(presentation_id, slide_number, text_content, image_filenames):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO slides(presentation_id, slide_number, text_content, image_filenames, created_at) VALUES(?,?,?,?,?)",
            (presentation_id, slide_number, text_content, json.dumps(image_filenames or []), datetime.datetime.utcnow().isoformat())
        )
        return cur.lastrowid

def insert_keyword(slide_id, keyword, source):
    kw = _normalize(keyword or "")
    if not kw:
        return None
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO keywords(slide_id, keyword, source, created_at) VALUES(?,?,?,?)",
            (slide_id, kw, source, datetime.datetime.utcnow().isoformat())
        )
        return cur.lastrowid

def list_slide_keywords(slide_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT keyword, source FROM keywords WHERE slide_id=? ORDER BY id ASC", (slide_id,))
        return [dict(keyword=r[0], source=r[1]) for r in cur.fetchall()]

def list_slides_by_presentation(presentation_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM slides WHERE presentation_id=? ORDER BY slide_number ASC", (presentation_id,))
        return [dict(r) for r in cur.fetchall()]

def search_slides(query, mode='keywords_any'):
    with get_conn() as conn:
        cur = conn.cursor()
        if mode == 'text':
            like = f"%{query}%"
            cur.execute("""SELECT s.*, p.filename
                           FROM slides s JOIN presentations p ON s.presentation_id=p.id
                           WHERE s.text_content LIKE ?
                           ORDER BY p.filename, s.slide_number""", (like,))
            return [dict(r) for r in cur.fetchall()]
        elif mode == 'keywords_like':
            terms = _split_terms(query)
            if not terms:
                return []
            clauses = " AND ".join([f"k.keyword LIKE ?" for _ in terms])
            cur.execute(f"""SELECT DISTINCT s.*, p.filename
                            FROM slides s
                            JOIN keywords k ON k.slide_id = s.id
                            JOIN presentations p ON s.presentation_id=p.id
                            WHERE {clauses}
                            ORDER BY p.filename, s.slide_number""", tuple([f"%{t}%" for t in terms]))
            return [dict(r) for r in cur.fetchall()]
        else:
            terms = _split_terms(query)
            if not terms:
                return []
            placeholders = ",".join("?"*len(terms))
            if mode == 'keywords_any':
                cur.execute(f"""SELECT DISTINCT s.*, p.filename
                                FROM slides s
                                JOIN keywords k ON k.slide_id = s.id
                                JOIN presentations p ON s.presentation_id=p.id
                                WHERE k.keyword IN ({placeholders})
                                ORDER BY p.filename, s.slide_number""", terms)
                return [dict(r) for r in cur.fetchall()]
            else:  # keywords_all
                cur.execute(f"""SELECT s.*, p.filename, COUNT(DISTINCT k.keyword) as match_cnt
                                FROM slides s
                                JOIN keywords k ON k.slide_id = s.id
                                JOIN presentations p ON s.presentation_id=p.id
                                WHERE k.keyword IN ({placeholders})
                                GROUP BY s.id
                                HAVING match_cnt = ?
                                ORDER BY p.filename, s.slide_number""", (*terms, len(terms)))
                rows = cur.fetchall()
                return [dict(r) for r in rows]
