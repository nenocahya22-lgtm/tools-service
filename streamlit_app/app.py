"""
streamlit_app/app.py — Versi legacy. Gunakan app.py di root project.
Jalankan: streamlit run app.py
"""

import streamlit as st
import os, sys

st.set_page_config(page_title="Smart Service HP", page_icon="🔧", layout="wide")

st.markdown("""
<style>
.stApp { background: #0A0A0F; color: #E5E7EB; }
.card {
    background: #1A1A2E; border: 1px solid #2D2D2D; border-radius: 12px;
    padding: 2rem; text-align: center; max-width: 500px; margin: 4rem auto;
}
</style>
<div class="card">
<h2 style="color:#C9A84C;">🔧 Smart Service HP</h2>
<p style="color:#9CA3AF;">Versi lengkap telah dipindahkan ke <code>app.py</code> (root project).</p>
<p style="color:#9CA3AF;">Jalankan:</p>
<code style="background:#2D2D2D;padding:0.5rem 1rem;border-radius:6px;display:inline-block;margin:0.5rem 0;color:#C9A84C;">
streamlit run app.py
</code>
</div>
""", unsafe_allow_html=True)

st.stop()
