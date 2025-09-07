
import os, io, json, shutil
import streamlit as st
from db import ensure_db, insert_presentation, insert_slide, insert_keyword, search_slides, list_slides_by_presentation
from ppt_extract import extract_slide_text_and_images
from keywording import suggest_keywords

APP_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(APP_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
IMG_DIR = os.path.join(DATA_DIR, "images")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)
ensure_db()

st.set_page_config(page_title="PPT Slide DB", layout="wide")
st.title("PPT Slide DB")

tab_ingest, tab_search = st.tabs(["登録（分解＆キーワード付与）", "検索"])

with tab_ingest:
    st.header("PPTXアップロードと分解")
    up = st.file_uploader("PowerPoint (.pptx) をアップロード", type=["pptx"])
    if up is not None:
        save_path = os.path.join(UPLOAD_DIR, up.name)
        with open(save_path, "wb") as f:
            f.write(up.read())
        st.success(f"アップロード完了: {save_path}")

        if st.button("スライド分解を実行"):
            try:
                pres_id = insert_presentation(filename=up.name, original_path=save_path)
                slides = extract_slide_text_and_images(save_path)
                st.write(f"スライド数: {len(slides)}")

                for s_num, text_content, image_blobs in slides:
                    # save images to files
                    stored_images = []
                    for (nm, blob) in image_blobs:
                        out_path = os.path.join(IMG_DIR, nm)
                        with open(out_path, "wb") as imf:
                            imf.write(blob)
                        stored_images.append(os.path.relpath(out_path, DATA_DIR))

                    slide_id = insert_slide(presentation_id=pres_id, slide_number=s_num,
                                            text_content=text_content, image_filenames=stored_images)

                    # Suggest candidates
                    cands = suggest_keywords(text_content, top_k=8)

                    with st.expander(f"スライド {s_num} のキーワード登録", expanded=False):
                        st.write("抽出テキスト（プレビュー）:")
                        st.code((text_content or "")[:1000])

                        sel = st.multiselect("候補から選択", cands, default=cands[:3], key=f"sel_{slide_id}")
                        manual = st.text_input("手動追加（スペース区切り）", key=f"man_{slide_id}")

                        if st.button(f"このスライドにキーワード保存", key=f"save_{slide_id}"):
                            # save selected
                            for kw in sel:
                                insert_keyword(slide_id, kw, source="candidate")
                            # save manual
                            manual_terms = [t.strip() for t in (manual or "").split() if t.strip()]
                            for kw in manual_terms:
                                insert_keyword(slide_id, kw, source="manual")
                            st.success("キーワードを保存しました。")

                st.info("分解とキーワード登録の準備が完了しました。必要に応じて各スライドの保存ボタンを押してください。")
            except Exception as e:
                st.error(f"エラー: {e}")

with tab_search:
    st.header("検索")
    q = st.text_input("クエリ（スペース区切り）")
    mode = st.selectbox("検索モード", ["keywords_any（いずれか一致）", "keywords_all（すべて一致）", "keywords_like（部分一致）", "text（本文に含む）"])
    mode_key = {"keywords_any（いずれか一致）": "keywords_any",
                "keywords_all（すべて一致）": "keywords_all",
                "keywords_like（部分一致）": "keywords_like", "text（本文に含む）": "text"}[mode]

    if st.button("検索する"):
        # Normalize query terms: split by space/comma/Japanese punctuation
        import re, unicodedata
        def _normalize_query(qs: str):
            qs = unicodedata.normalize("NFKC", qs or "")
            # Replace separators with spaces
            qs = re.sub(r"[，、,;/]+", " ", qs)
            qs = re.sub(r"[\s\u3000]+", " ", qs)
            return qs.strip().lower()

        qn = _normalize_query(q)
        rows = []
        if mode_key == "keywords_like":
            # manual LIKE query
            import sqlite3
            from db import get_conn
            terms = [t for t in qn.split(" ") if t]
            if terms:
                # Build AND over terms for LIKE
                clauses = " AND ".join([f"k.keyword LIKE ?" for _ in terms])
                with get_conn() as conn:
                    cur = conn.cursor()
                    cur.execute(f"""SELECT DISTINCT s.*, p.filename
                                     FROM slides s
                                     JOIN keywords k ON k.slide_id = s.id
                                     JOIN presentations p ON s.presentation_id=p.id
                                     WHERE {clauses}
                                     ORDER BY p.filename, s.slide_number""", tuple([f"%{t}%" for t in terms]))
                    rows = [dict(r) for r in cur.fetchall()]
        else:
            rows = search_slides(qn, mode=mode_key)

        st.write(f"ヒット数: {len(rows)}")

if not rows:
    st.caption("※ 見つからない場合は「keywords_like（部分一致）」や区切り文字（スペース/カンマ/読点）を確認してください。")
for r in rows:
            st.markdown("---")
            st.markdown(f"**ファイル**: {r.get('filename')}　**スライド**: {r.get('slide_number')}")
            st.markdown("**抜粋テキスト**")
            st.code((r.get('text_content') or "")[:1000])
            # fetch keywords for this slide
            import sqlite3
            from db import get_conn
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT keyword, source FROM keywords WHERE slide_id=? ORDER BY id ASC", (r['id'],))
                kws = cur.fetchall()
            if kws:
                disp = [f"{kw} ({src})" for kw, src in kws]
                st.write("**登録キーワード**: ", ", ".join(disp))
            # provide path to original file (relative)
            st.caption("※ 検索はDB内のテキストと登録キーワードに対して実行しています。元のPPTXは data/uploads/ に保存されています。")

