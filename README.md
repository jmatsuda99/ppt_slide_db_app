
# PPT Slide DB (Streamlit)

A simple Streamlit app to:
- Split a PowerPoint (`.pptx`) into **slide-level records**
- **Suggest keywords** per slide (YAKE if available, else basic TF)
- **Select candidates and add manual keywords**, then save to SQLite
- **Search** by keywords or text and view results slide-by-slide

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
streamlit run app.py
```

## Notes
- Slide **images are not rendered** (python-pptx can't rasterize). We extract slide **text** and list image filenames (if any).
- Results show: file name, slide number, extracted text snippet, and registered keywords.
- Database file is `data/slide_db.sqlite`. Uploaded PPTX files are stored under `data/uploads/`.

