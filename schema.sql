
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS presentations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  filename TEXT NOT NULL,
  original_path TEXT NOT NULL,
  uploaded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS slides (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  presentation_id INTEGER NOT NULL,
  slide_number INTEGER NOT NULL,
  text_content TEXT,
  image_filenames TEXT, -- JSON array of stored image file paths
  created_at TEXT NOT NULL,
  FOREIGN KEY(presentation_id) REFERENCES presentations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS keywords (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slide_id INTEGER NOT NULL,
  keyword TEXT NOT NULL,
  source TEXT NOT NULL, -- 'candidate' or 'manual'
  created_at TEXT NOT NULL,
  FOREIGN KEY(slide_id) REFERENCES slides(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_keywords_kw ON keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_slides_text ON slides(id);


-- Ensure no duplicate keywords per slide
CREATE UNIQUE INDEX IF NOT EXISTS uq_keywords_slide_kw ON keywords(slide_id, keyword);
