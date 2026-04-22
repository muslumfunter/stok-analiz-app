import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
import plotly.graph_objects as go
import io
import os
from datetime import datetime

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Stok Analiz Dashboard", page_icon="📦", layout="wide")

# ==========================================
# 🔒 GÜVENLİK (ŞİFRE) EKRANI
# ==========================================
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown("<h2 style='text-align: center; color: #2c3e50;'>🔒 Yönetici Girişi</h2>", unsafe_allow_html=True)
            password = st.text_input("Şifre", type="password", label_visibility="collapsed", placeholder="Şifrenizi girin...")
            if st.button("Giriş Yap", use_container_width=True):
                if password == "StokAnaliz2026!":
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("❌ Hatalı şifre!")
        st.stop()

check_password()

# ==========================================
# 🎨 ULTRA KOMPAKT TASARIM (CSS)
# ==========================================
st.markdown("""
    <style>
    header { display: none !important; }
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; padding-left: 1.5rem !important; padding-right: 1.5rem !important; }
    h1, h2, h3 { margin-top: 0rem !important; margin-bottom: 0.2rem !important; padding-top: 0rem !important; padding-bottom: 0rem !important; }
    hr { margin-top: 0.2rem !important; margin-bottom: 0.2rem !important; border-top: 1px solid #d1d8e0;}
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] { height: 35px; padding: 0px 10px; }
    </style>
""", unsafe_allow_html=True)

# --- BAŞLIK VE GÜVENLİ ÇIKIŞ ---
col_t1, col_t3 = st.columns([10, 1])
with col_t1: st.markdown("### 📦 Operasyon Kalite - Sayım Farkı Dashboard")
with col_t3:
    if st.button("🚪 Çıkış", use_container_width=True):
        st.session_state.clear()
        st.session_state["authenticated"] = False
        st.rerun()

# --- YARDIMCI FONKSİYONLAR ---
def format_money(x):
    try:
        val = float(x)
        is_negative = val < 0
        abs_x = abs(val)
        sign = "-" if is_negative else ""
        if abs_x >= 1_000_000: return f"{sign}{abs_x/1_000_000:.1f}M"
        elif abs_x >= 1_000: return f"{sign}{abs_x/1_000:.1f}K"
        return f"{sign}{abs_x:.0f}"
    except: return str(x)

izlenecek_urunler = ['taşınabilir bilgisayar', 'cep telefonu', 'tabletler', 'IPL cihazları']

# --- DOSYA YÜKLEME ALANI ---
c1, c2 = st.columns([1, 1])
with c1:
    st.caption("📊 Analiz Raporlarını Yükleyin (En az 2 adet)")
    uploaded_files = st.file_uploader("Raporlar", type=['xlsx'], accept_multiple_files=True, label_visibility="collapsed")
with c2:
    st.caption("📌 Varsa Mevcut Takip Listesini Yükleyin (Opsiyonel)")
    track_file_upload = st.file_uploader("Takip Listesi", type=['xlsx', 'csv'], accept_multiple_files=False, label_visibility="collapsed")

# --- ANALİZ VE DASHBOARD ---
if len(uploaded_files) >= 2:
    with st.spinner("Veriler işleniyor..."):
        # 1. Raporları Oku
        liste = []
        for f in uploaded_files:
            df = pd.read_excel(f, header=0)
            df.columns = df.columns.str.strip()
            kisa_tarih = f.name.replace(".xlsx", "")[:2]
            df['Rapor_Tarihi'] = kisa_tarih
            liste.append(df)
        
        df_master = pd.concat(liste, ignore_index=True).sort_values(by='Rapor_Tarihi')
        df_master['Kayıp_Adet'] = df_master['Stokta Bulunan'].apply(lambda x: x if x > 0 else 0)
        df_master['Toplam Fiyat'] = df_master['Toplam Fiyat'].fillna(0)
        son_tarih = df_master['Rapor_Tarihi'].iloc[-1]
        
        depo_col = next((c for c in df_master.columns if any(x in c.lower() for x in ['depo', 'plant', 'tesis', 'lokasyon'])), None)
        if depo_col:
            df_master[depo_col] = df_master[depo_col].astype(str).str.replace(r'\.0$', '', regex=True)
            mevcut_depolar = sorted([d for d in df_master[depo_col].unique() if str(d).lower() != 'nan'])
            secilen_depolar = st.multiselect("🏢 *Depo Filtresi:*", options=mevcut_depolar, default=mevcut_depolar)
            aktif_df = df_master[df_master[depo_col].isin(secilen_depolar)].copy()
        else: aktif_df = df_master.copy()

        # 2. Takip Listesini Hafızaya Al (Session State)
        if "takip_df" not in st.session_state:
            if track_file_upload is not None:
                if track_file_upload.name.endswith('.csv'):
                    st.session_state.takip_df = pd.read_csv(track_file_upload)
                else:
                    st.session_state.takip_df = pd.read_excel(track_file_upload)
            else:
                st.session_state.takip_df = pd.DataFrame(columns=['malzeme no', 'Eklenme_Tarihi', 'Not'])
        
        # Malzeme no tipini sabitle
        st.session_state.takip_df['malzeme no'] = st.session_state.takip_df['malzeme no'].astype(str)

        tab1, tab2, tab4, tab3, tab5 = st.tabs(["📈 Genel", "🏢 Kategoriler", "🏭 Depolar", "🔍 Dive Deep", "📌 Takip Listesi (Export)"])

        # (Tab 1, 2, 3, 4 kodları öncekiyle aynı kalabilir, kısalık için Tab 5'e odaklanıyorum)
        with tab1: st.info("Dashboard aktif. Detaylar için sekmeleri gezin.")

        # --- 📌 TAKİP LİSTESİ (EXPORT/IMPORT MODÜLÜ) ---
        with tab5:
            st.markdown("#### 📌 Takip Listesi Yönetimi")
            st.info("💡 Burada yaptığınız değişikliklerin kalıcı olması için işiniz bitince en alttaki *'Güncel Listeyi Dışa Aktar'* butonuyla dosyayı ortak alanınıza kaydedin.")

            # Yeni Ekleme Formu
            with st.expander("➕ Listeye Yeni Ürün Ekle", expanded=False):
                mevcut_tum_skular = sorted([str(s) for s in df_master['malzeme no'].unique() if str(s).lower() != 'nan'])
                c_y1, c_y2 = st.columns([1, 2])
                sec_sku = c_y1.selectbox("SKU Seç:", options=[""] + mevcut_tum_skular)
                not_input = c_y2.text_input("Notunuz:")
                if st.button("Listeye Ekle"):
                    if sec_sku and sec_sku not in st.session_state.takip_df['malzeme no'].values:
                        tam_tarih = f"{son_tarih}.{datetime.now().strftime('%m.%Y')}"
                        yeni_satir = pd.DataFrame([{'malzeme no': sec_sku, 'Eklenme_Tarihi': tam_tarih, 'Not': not_input}])
                        st.session_state.takip_df = pd.concat([st.session_state.takip_df, yeni_satir], ignore_index=True)
                        st.success(f"{sec_sku} listeye eklendi!")
                        st.rerun()

            # Takip Listesi Tablosu ve Analiz
            if not st.session_state.takip_df.empty:
                track_skus = st.session_state.takip_df['malzeme no'].tolist()
                t_analiz_df = df_master[df_master['malzeme no'].astype(str).isin(track_skus)].copy()
                
                if not t_analiz_df.empty:
                    # Raporlardaki güncel stok durumlarını getir
                    t_pivot = t_analiz_df.pivot_table(index='malzeme no', columns='Rapor_Tarihi', values='Stokta Bulunan', aggfunc='sum').reset_index()
                    t_pivot['malzeme no'] = t_pivot['malzeme no'].astype(str)
                    gosterim_df = pd.merge(st.session_state.takip_df, t_pivot, on='malzeme no', how='left').fillna(0)
                    
                    st.dataframe(gosterim_df, use_container_width=True, hide_index=True)
                else:
                    st.dataframe(st.session_state.takip_df, use_container_width=True)

                st.markdown("---")
                
                # --- EXPORT (DIŞA AKTAR) BUTONU ---
                col_ex1, col_ex2 = st.columns([1, 1])
                
                # Excel olarak hazırla
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    st.session_state.takip_df.to_excel(writer, index=False, sheet_name='TakipListesi')
                
                col_ex1.download_button(
                    label="📥 Güncel Takip Listesini Dışa Aktar (Excel)",
                    data=buffer.getvalue(),
                    file_name=f"Takip_Listesi_Guncel_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
                    mime="application/vnd.ms-excel",
                    use_container_width=True
                )
                
                if col_ex2.button("🗑️ Tüm Listeyi Temizle (Sıfırla)"):
                    st.session_state.takip_df = pd.DataFrame(columns=['malzeme no', 'Eklenme_Tarihi', 'Not'])
                    st.rerun()
            else:
                st.warning("Takip listeniz şu an boş. Üstten ürün ekleyebilir veya ortak alandaki dosyanızı yukarıdan yükleyebilirsiniz.")

else:
    st.info("Hoş geldiniz! Analize başlamak için lütfen sol üstteki alandan Excel dosyalarınızı yükleyin.")
