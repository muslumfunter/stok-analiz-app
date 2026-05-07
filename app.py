import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
import plotly.graph_objects as go
import io
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
# 🎨 ULTRA-KOMPAKT TASARIM (CSS)
# ==========================================
st.markdown("""
    <style>
    header { display: none !important; }
    .block-container { padding-top: 0.5rem !important; padding-bottom: 0rem !important; padding-left: 1.5rem !important; padding-right: 1.5rem !important;}
    h1, h2, h3 { margin-top: 0rem !important; margin-bottom: 0.5rem !important; padding-top: 0rem !important; }
    hr { margin-top: 0.2rem !important; margin-bottom: 0.2rem !important; border-top: 1px solid #d1d8e0;}
    
    div[data-testid="stFileUploader"] { padding: 0px !important; margin-bottom: -15px !important;}
    section[data-testid="stFileUploadDropzone"] { 
        padding: 0.5rem !important; 
        min-height: 50px !important; 
        border: 1px dashed #3498db !important;
        background-color: #f8fbff !important;
    }
    div[data-testid="stFileUploadDropzone"] > button { display: none !important; } 
    ul[data-testid="stUploadedFileList"] { display: none !important; } 
    
    .stTabs { margin-top: 0.5rem !important; }
    .stTabs [data-baseweb="tab"] { height: 35px; padding: 0px 15px; }
    div[data-testid="stMetricValue"] > div { font-size: 1.3rem !important; font-weight: bold;}
    div[data-testid="stMetricLabel"] > label { font-size: 0.8rem !important; margin-bottom: -0.2rem !important;}
    .stMultiSelect { margin-bottom: -1rem !important; }
    div[data-baseweb="select"] > div { min-height: 30px !important; }
    
    th.col_heading { text-align: center !important; }
    </style>
""", unsafe_allow_html=True)

# --- ÜST PANEL ---
col_t1, col_t3 = st.columns([10, 1])
with col_t1: st.markdown("### 📦 Operasyon Kalite - Sayım Farkı Dashboard")
with col_t3:
    if st.button("🚪 Çıkış", use_container_width=True):
        st.session_state.clear()
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

def get_colors_by_value(values):
    return ['#e74c3c' if val > 0 else '#2ecc71' for val in values]

def label_bars(ax, is_money=False):
    for p in ax.patches:
        val = p.get_height()
        if val != 0:
            label = format_money(val) if is_money else f"{val:.0f}"
            ax.annotate(label, (p.get_x() + p.get_width() / 2., val), ha='center', va='center', xytext=(0, 6), textcoords='offset points', fontsize=7, fontweight='bold', color="#2c3e50")

izlenecek_urunler = ['taşınabilir bilgisayar', 'cep telefonu', 'tabletler', 'IPL cihazları']

# --- ANA EKRAN DOSYA YÜKLEME (ANA DASHBOARD İÇİN) ---
st.caption("📊 Analiz Edilecek Günlük Raporları Yükleyin (İlk 4 Sekme İçin)")
uploaded_files = st.file_uploader("Raporlar", type=['xlsx'], accept_multiple_files=True, label_visibility="collapsed", key="main_uploader")

if uploaded_files:
    st.markdown(f"<div style='background-color:#e8f8f5; padding:5px; border-radius:5px; border:1px solid #2ecc71; color:#145a32; font-size:12px; font-weight:bold; margin-top:5px;'>✅ {len(uploaded_files)} Adet Rapor Analize Hazır</div>", unsafe_allow_html=True)

# --- ANALİZ VE DASHBOARD ---
if len(uploaded_files) >= 2:
    with st.spinner("Veriler işleniyor, lütfen bekleyin..."):
        liste = []
        for f in uploaded_files:
            df = pd.read_excel(f, header=0)
            df.columns = df.columns.astype(str).str.strip()
            
            tarih_str = f.name.replace(".xlsx", "")[:5] 
            df['Rapor_Tarihi'] = tarih_str
            try:
                df['Gercek_Tarih'] = pd.to_datetime(tarih_str, format='%d.%m')
            except:
                df['Gercek_Tarih'] = pd.to_datetime('1900-01-01')
                
            liste.append(df)
        
        df_master = pd.concat(liste, ignore_index=True).sort_values(by='Gercek_Tarih')
        
        if 'malzeme no' in df_master.columns:
            df_master['malzeme no'] = df_master['malzeme no'].astype(str)

        df_master['Kayıp_Adet'] = df_master['Stokta Bulunan'].apply(lambda x: x if x > 0 else 0)
        df_master['Buldum_Adet'] = df_master['Stokta Bulunan'].apply(lambda x: x if x < 0 else 0)
        df_master['Toplam Fiyat'] = df_master['Toplam Fiyat'].fillna(0)
        df_master['Kayıp_Tutar'] = df_master.apply(lambda row: abs(row['Toplam Fiyat']) if row['Stokta Bulunan'] > 0 else 0, axis=1)
        df_master['Buldum_Tutar'] = df_master.apply(lambda row: -abs(row['Toplam Fiyat']) if row['Stokta Bulunan'] < 0 else 0, axis=1)
        
        all_dates_df = df_master[['Rapor_Tarihi', 'Gercek_Tarih']].drop_duplicates().sort_values('Gercek_Tarih')
        benzersiz_tarihler = all_dates_df['Rapor_Tarihi'].tolist()
        ilk_tarih = benzersiz_tarihler[0]
        son_tarih = benzersiz_tarihler[-1] 
        
        depo_col = next((c for c in df_master.columns if any(x in c.lower() for x in ['depo', 'plant', 'tesis', 'lokasyon'])), None)
        
        if depo_col:
            df_master[depo_col] = df_master[depo_col].astype(str).str.replace(r'\.0$', '', regex=True)
            mevcut_depolar = sorted([d for d in df_master[depo_col].unique() if str(d).lower() != 'nan'])
            secilen_depolar = st.multiselect("🏢 **Ana Dashboard Depo Filtresi:**", options=mevcut_depolar, default=mevcut_depolar)
            aktif_df = df_master[df_master[depo_col].isin(secilen_depolar)].copy() if secilen_depolar else df_master.iloc[0:0].copy()
        else:
            aktif_df = df_master.copy()

        if aktif_df.empty:
            st.warning("⚠️ Lütfen analizleri görmek için yukarıdan en az bir depo seçin.")
        else:
            tab1, tab2, tab4, tab3, tab5 = st.tabs(["📈 Genel Dashboard", "🏢 Kategori Detayı", "🏭 Depolar (Top 20)", "🔍 Dive Deep", "🏢 0020 Eşitleme Analizi"])
            pdf_buffer = io.BytesIO()
            excel_buffer = io.BytesIO()

            with PdfPages(pdf_buffer) as pdf:
                # --- TAB 1: GENEL DASHBOARD ---
                with tab1:
                    guncel_master_df = aktif_df[aktif_df['Rapor_Tarihi'] == son_tarih]
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(f"🔻 Toplam Kayıp (Adet) - Gün {son_tarih}", f"{guncel_master_df['Kayıp_Adet'].sum():,.0f}")
                    c2.metric(f"🔻 Toplam Kayıp (TL)", format_money(guncel_master_df['Kayıp_Tutar'].sum()))
                    c3.metric(f"🟢 Toplam Buldum (Adet)", f"{abs(guncel_master_df['Buldum_Adet'].sum()):,.0f}")
                    c4.metric(f"🟢 Toplam Buldum (TL)", format_money(abs(guncel_master_df['Buldum_Tutar'].sum())))
                    
                    if depo_col:
                        depo_ozet = guncel_master_df.groupby(depo_col)[['Kayıp_Adet', 'Kayıp_Tutar', 'Buldum_Adet', 'Buldum_Tutar']].sum().reset_index()
                        html_etiketler = "<div style='display:flex; flex-wrap:wrap; gap:8px; margin-top:5px; margin-bottom:5px;'>"
                        for _, row in depo_ozet.iterrows():
                            if str(row[depo_col]).lower() == 'nan' or str(row[depo_col]).lower() == 'none': continue
                            d_kayip_a = row['Kayıp_Adet']
                            d_kayip_t = format_money(row['Kayıp_Tutar'])
                            d_buldum_a = abs(row['Buldum_Adet'])
                            d_buldum_t = format_money(abs(row['Buldum_Tutar']))
                            html_etiketler += f"<div style='background-color:#ffffff; border: 1px solid #d1d8e0; border-radius: 4px; padding: 4px 10px; font-size:12px; color:#2c3e50; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'><b>🏢 {row[depo_col]}</b> &nbsp;|&nbsp; <span style='color:#c0392b;'>🔻 K: <b>{d_kayip_a:,.0f}</b> <span style='font-size:10px;'>({d_kayip_t})</span></span> &nbsp;|&nbsp; <span style='color:#1e8449;'>🟢 B: <b>{d_buldum_a:,.0f}</b> <span style='font-size:10px;'>({d_buldum_t})</span></span></div>"
                        html_etiketler += "</div>"
                        st.markdown(html_etiketler, unsafe_allow_html=True)

                    st.markdown("<hr style='margin: 0.2rem 0 !important;'>", unsafe_allow_html=True)

                    dash_df = aktif_df[aktif_df['Ürün Tipi'].str.lower().isin([x.lower() for x in izlenecek_urunler])]
                    dash_grouped = dash_df.groupby(['Ürün Tipi', 'Rapor_Tarihi', 'Gercek_Tarih'])[['Stokta Bulunan', 'Toplam Fiyat', 'Kayıp_Adet', 'Buldum_Adet', 'Kayıp_Tutar', 'Buldum_Tutar']].sum().reset_index()
                    
                    cols = st.columns(4)
                    for i, urun in enumerate(izlenecek_urunler):
                        u_data_raw = dash_grouped[dash_grouped['Ürün Tipi'].str.lower() == urun.lower()]
                        u_data = pd.merge(all_dates_df, u_data_raw, on=['Rapor_Tarihi', 'Gercek_Tarih'], how='left').fillna(0)
                        
                        with cols[i]:
                            f_m = go.Figure()
                            f_m.add_trace(go.Bar(x=u_data['Rapor_Tarihi'], y=u_data['Kayıp_Adet'], name='Kayıp', marker_color='#e74c3c', text=u_data['Kayıp_Adet'].apply(lambda x: f"{x:.0f}" if x != 0 else ""), textposition='auto', textfont=dict(size=9)))
                            f_m.add_trace(go.Bar(x=u_data['Rapor_Tarihi'], y=u_data['Buldum_Adet'], name='Buldum', marker_color='#2ecc71', text=u_data['Buldum_Adet'].apply(lambda x: f"{x:.0f}" if x != 0 else ""), textposition='auto', textfont=dict(size=9)))
                            f_m.update_layout(barmode='relative', title=f"<b>{urun.upper()}</b><br><span style='font-size:10px;'>FARK ADET</span>", margin=dict(t=35, b=0, l=0, r=0), height=140, showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#2c3e50', size=10))
                            f_m.update_xaxes(type='category', visible=True, tickfont=dict(size=8))
                            st.plotly_chart(f_m, use_container_width=True, key=f"s_a_{i}")
                            
                            f_t = go.Figure()
                            f_t.add_trace(go.Bar(x=u_data['Rapor_Tarihi'], y=u_data['Kayıp_Tutar'], name='Kayıp T', marker_color='#e74c3c', text=u_data['Kayıp_Tutar'].apply(lambda x: format_money(x) if x != 0 else ""), textposition='auto', textfont=dict(size=9)))
                            f_t.add_trace(go.Bar(x=u_data['Rapor_Tarihi'], y=u_data['Buldum_Tutar'], name='Buldum T', marker_color='#2ecc71', text=u_data['Buldum_Tutar'].apply(lambda x: format_money(x) if x != 0 else ""), textposition='auto', textfont=dict(size=9)))
                            f_t.update_layout(barmode='relative', title="<span style='font-size:10px;'>TOPLAM FARK (TL)</span>", margin=dict(t=20, b=0, l=0, r=0), height=140, showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#2c3e50', size=10))
                            f_t.update_xaxes(type='category', title_text="Gün", title_font=dict(size=9), tickfont=dict(size=9))
                            st.plotly_chart(f_t, use_container_width=True, key=f"t_d_{i}")

                    with st.expander(f"📋 Güncel Kategori Özeti (Gün {son_tarih})", expanded=True):
                        guncel_dash = dash_grouped[dash_grouped['Rapor_Tarihi'] == son_tarih].copy()
                        if guncel_dash.empty:
                            st.info(f"{son_tarih} tarihinde bu kategorilerde veri bulunamadı.")
                        else:
                            guncel_dash = guncel_dash[['Ürün Tipi', 'Kayıp_Adet', 'Buldum_Adet', 'Stokta Bulunan', 'Toplam Fiyat']]
                            guncel_dash.columns = ['Ürün Tipi', 'Güncel Kayıp (Adet)', 'Güncel Buldum (Adet)', 'Net Adet', 'Net Tutar (TL)']
                            guncel_dash = guncel_dash[(guncel_dash['Güncel Kayıp (Adet)'] != 0) | (guncel_dash['Güncel Buldum (Adet)'] != 0) | (guncel_dash['Net Adet'] != 0)]
                            
                            if guncel_dash.empty:
                                st.info(f"Gün {son_tarih} için hareketi olan kategori bulunamadı.")
                            else:
                                st.dataframe(guncel_dash.style.format({
                                    'Güncel Kayıp (Adet)': "{:,.0f}", 
                                    'Güncel Buldum (Adet)': "{:,.0f}", 
                                    'Net Adet': "{:,.0f}", 
                                    'Net Tutar (TL)': "{:,.0f}"
                                }), use_container_width=True, hide_index=True)

                    fig1, axes = plt.subplots(nrows=2, ncols=4, figsize=(16, 8))
                    plt.subplots_adjust(hspace=0.4, wspace=0.3)
                    fig1.patch.set_facecolor('#f4f6f9')
                    for i, urun in enumerate(izlenecek_urunler):
                        u_data_raw = dash_grouped[dash_grouped['Ürün Tipi'].str.lower() == urun.lower()]
                        u_data = pd.merge(all_dates_df, u_data_raw, on=['Rapor_Tarihi', 'Gercek_Tarih'], how='left').fillna(0)
                        
                        if not u_data.empty: 
                            m_colors = get_colors_by_value(u_data['Stokta Bulunan'])
                            ax_m = sns.barplot(data=u_data, x='Rapor_Tarihi', y='Stokta Bulunan', ax=axes[0, i], palette=m_colors)
                            axes[0, i].set_title(f'{urun.upper()}\nNET FARK ADET', fontsize=10, fontweight='bold', color='#2c3e50')
                            axes[0, i].tick_params(colors='#2c3e50', labelsize=8)
                            axes[0, i].set_facecolor('#f4f6f9')
                            axes[0, i].set_xlabel("Gün", fontsize=8)
                            label_bars(ax_m, is_money=False)
                            
                            t_colors = get_colors_by_value(u_data['Toplam Fiyat'])
                            ax_t = sns.barplot(data=u_data, x='Rapor_Tarihi', y='Toplam Fiyat', ax=axes[1, i], palette=t_colors)
                            axes[1, i].set_title(f'NET FARK DEĞERİ (TL)', fontsize=10, fontweight='bold', color='#2c3e50')
                            axes[1, i].tick_params(colors='#2c3e50', labelsize=8)
                            axes[1, i].set_facecolor('#f4f6f9')
                            axes[1, i].set_xlabel("Gün", fontsize=8)
                            label_bars(ax_t, is_money=True)
                        else:
                            axes[0, i].set_title(f'{urun.upper()}\n(Veri Yok)', fontsize=10, fontweight='bold')
                            axes[1, i].set_title(f'(Veri Yok)', fontsize=10, fontweight='bold')
                    plt.suptitle(f'SAYIM FARKI DASHBOARD - Gün {son_tarih}\n(Kırmızı: Kayıp | Yeşil: Buldum)', fontsize=16, fontweight='bold', color='#2c3e50', y=0.98)
                    pdf.savefig(fig1, bbox_inches='tight')
                    plt.close(fig1)

                # --- TAB 2: KATEGORİ DETAYI ---
                with tab2:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**🔻 Güncel Kayıp En Yüksek İlk 10 (Gün {son_tarih})**")
                        kayip_df = guncel_master_df[guncel_master_df['Kayıp_Tutar'] > 0]
                        t10_s = kayip_df.groupby('Buying Category Name')['Kayıp_Tutar'].sum().sort_values(ascending=False).head(10)
                        if not t10_s.empty:
                            f2 = go.Figure(go.Bar(x=t10_s.values, y=t10_s.index, orientation='h', marker=dict(color=t10_s.values, colorscale='Reds')))
                            f2.update_layout(yaxis={'categoryorder':'total ascending'}, height=400, margin=dict(t=0, l=0, r=0, b=0), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#2c3e50'))
                            st.plotly_chart(f2, use_container_width=True)
                            
                            fig2, ax_top = plt.subplots(figsize=(8, 6))
                            fig2.patch.set_facecolor('#f4f6f9')
                            ax_top.set_facecolor('#f4f6f9')
                            sns.barplot(x=t10_s.values, y=t10_s.index, palette='Reds_r', ax=ax_top)
                            plt.title(f'GÜNCEL KAYIP (TL) - {son_tarih}', fontsize=12, fontweight='bold', color='#2c3e50')
                            ax_top.tick_params(colors='#2c3e50', labelsize=8)
                            label_bars(ax_top, is_money=True)
                            pdf.savefig(fig2, bbox_inches='tight')
                            plt.close(fig2)
                        else:
                            st.info("Kayıp kaydı bulunamadı.")

                    with col2:
                        st.markdown(f"**🟢 Güncel Buldum En Yüksek İlk 10 (Gün {son_tarih})**")
                        buldum_df = guncel_master_df[guncel_master_df['Buldum_Tutar'] < 0].copy()
                        buldum_df['Buldum_Tutar_Abs'] = buldum_df['Buldum_Tutar'].abs()
                        t10_f = buldum_df.groupby('Buying Category Name')['Buldum_Tutar_Abs'].sum().sort_values(ascending=False).head(10)
                        if not t10_f.empty:
                            f3 = go.Figure(go.Bar(x=t10_f.values, y=t10_f.index, orientation='h', marker=dict(color=t10_f.values, colorscale='Greens')))
                            f3.update_layout(yaxis={'categoryorder':'total ascending'}, height=400, margin=dict(t=0, l=0, r=0, b=0), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#2c3e50'))
                            st.plotly_chart(f3, use_container_width=True)
                            
                            fig3, ax_cat = plt.subplots(figsize=(8, 6))
                            fig3.patch.set_facecolor('#f4f6f9')
                            ax_cat.set_facecolor('#f4f6f9')
                            sns.barplot(x=t10_f.values, y=t10_f.index, palette='Greens_r', ax=ax_cat)
                            plt.title(f'GÜNCEL BULDUM (TL) - {son_tarih}', fontsize=12, fontweight='bold', color='#2c3e50')
                            ax_cat.tick_params(colors='#2c3e50', labelsize=8)
                            label_bars(ax_cat, is_money=True)
                            pdf.savefig(fig3, bbox_inches='tight')
                            plt.close(fig3)
                        else:
                            st.info("Buldum kaydı bulunamadı.")

                # --- TAB 4: DEPOLAR TOP 20 ---
                with tab4:
                    if depo_col:
                        st.markdown(f"**🏭 Depo Bazında Güncel (Gün {son_tarih}) İlk 20 SKU Detayı**")
                        guncel_tab4_df = aktif_df[aktif_df['Rapor_Tarihi'] == son_tarih]
                        if not guncel_tab4_df.empty:
                            depolar_listesi = sorted([d for d in guncel_tab4_df[depo_col].unique() if str(d).lower() != 'nan' and str(d).lower() != 'none'])
                            for d in depolar_listesi:
                                st.markdown(f"<h5 style='color:#2c3e50; margin-top:20px !important; border-bottom:2px solid #3498db; padding-bottom:5px;'>🏢 {d} Deposu</h5>", unsafe_allow_html=True)
                                d_data = guncel_tab4_df[guncel_tab4_df[depo_col] == d]
                                sku_d = d_data.groupby(['malzeme no', 'Malzeme Tanımı', 'Ürün Tipi'])[['Kayıp_Adet', 'Kayıp_Tutar', 'Buldum_Adet', 'Buldum_Tutar']].sum().reset_index()
                                
                                top_k = sku_d[sku_d['Kayıp_Adet'] > 0].sort_values(by='Kayıp_Tutar', ascending=False).head(20)
                                top_b = sku_d[sku_d['Buldum_Adet'] < 0].copy()
                                top_b['Buldum_Adet'] = top_b['Buldum_Adet'].abs()
                                top_b['Buldum_Tutar'] = top_b['Buldum_Tutar'].abs()
                                top_b = top_b.sort_values(by='Buldum_Tutar', ascending=False).head(20)
                                
                                col_k, col_b = st.columns(2)
                                with col_k:
                                    st.markdown("<span style='color:#c0392b; font-weight:bold;'>🔻 İlk 20 Kayıp (Tutar Bazında)</span>", unsafe_allow_html=True)
                                    if not top_k.empty: st.dataframe(top_k[['malzeme no', 'Malzeme Tanımı', 'Kayıp_Adet', 'Kayıp_Tutar']].style.format({'Kayıp_Adet': "{:,.0f}", 'Kayıp_Tutar': format_money}), use_container_width=True, hide_index=True)
                                with col_b:
                                    st.markdown("<span style='color:#1e8449; font-weight:bold;'>🟢 İlk 20 Buldum (Tutar Bazında)</span>", unsafe_allow_html=True)
                                    if not top_b.empty: st.dataframe(top_b[['malzeme no', 'Malzeme Tanımı', 'Buldum_Adet', 'Buldum_Tutar']].style.format({'Buldum_Adet': "{:,.0f}", 'Buldum_Tutar': format_money}), use_container_width=True, hide_index=True)

                # --- TAB 3: DIVE DEEP ---
                with tab3:
                    st.markdown("**🔍 Malzeme Bazlı Analiz (SKU)**")
                    if depo_col:
                        col_d, col_u, col_dr, col_s = st.columns(4)
                        sec_depo_dive = col_d.multiselect("🏢 Depo:", options=mevcut_depolar, default=mevcut_depolar, key="dive_depo_filter")
                        deep_base_df = df_master[df_master[depo_col].isin(sec_depo_dive)].copy()
                    else:
                        col_u, col_dr, col_s = st.columns(3)
                        deep_base_df = df_master.copy()
                        
                    dp = deep_base_df.pivot_table(index=['Ürün Tipi', 'malzeme no', 'Malzeme Tanımı'], columns='Rapor_Tarihi', values=['Stokta Bulunan', 'Birim Fiyat'], aggfunc={'Stokta Bulunan': 'sum', 'Birim Fiyat': 'mean'}).fillna(0)
                    
                    if len(dp.columns.levels[1]) > 1:
                        if ('Stokta Bulunan', ilk_tarih) in dp.columns and ('Stokta Bulunan', son_tarih) in dp.columns:
                            dp[('Analiz', 'Fark_Adet')] = dp[('Stokta Bulunan', son_tarih)] - dp[('Stokta Bulunan', ilk_tarih)]
                        else:
                            dp[('Analiz', 'Fark_Adet')] = 0
                            
                        def b_d(r):
                            if ('Stokta Bulunan', son_tarih) in r and r[('Stokta Bulunan', son_tarih)] == 0: return "EŞİTLENDİ"
                            elif r[('Analiz', 'Fark_Adet')] > 0: return "KAYIP"
                            elif r[('Analiz', 'Fark_Adet')] < 0: return "BULDUM"
                            else: return "SABİT"
                            
                        dp[('Analiz', 'DURUM')] = dp.apply(b_d, axis=1)
                        gf = dp['Birim Fiyat'].max(axis=1)
                        if ('Stokta Bulunan', son_tarih) in dp.columns:
                            dp[('Analiz', 'Güncel_Tutar_TL')] = dp[('Stokta Bulunan', son_tarih)] * gf
                        else:
                            dp[('Analiz', 'Güncel_Tutar_TL')] = 0
                            
                        df_f = dp[(dp[('Stokta Bulunan', son_tarih)] != 0) | (dp[('Analiz', 'Fark_Adet')] != 0)].sort_values(by=[('Analiz', 'Güncel_Tutar_TL')], ascending=False)
                        if 'Birim Fiyat' in df_f.columns.get_level_values(0): df_f = df_f.drop(columns=['Birim Fiyat'])
                        
                        st_i = col_u.multiselect("📊 Ürün Tipi:", options=sorted(df_f.index.get_level_values('Ürün Tipi').unique()))
                        m_d = df_f[('Analiz', 'DURUM')].unique().tolist()
                        s_d = col_dr.multiselect("📌 Durum:", options=m_d, default=[d for d in ["KAYIP", "BULDUM", "EŞİTLENDİ", "SABİT"] if d in m_d])
                        s_sku = col_s.multiselect("🔍 Malzeme No:", options=df_f.index.get_level_values('malzeme no').unique())
                        
                        f_df = df_f.copy()
                        if st_i: f_df = f_df[f_df.index.get_level_values('Ürün Tipi').isin(st_i)]
                        if s_d: f_df = f_df[f_df[('Analiz', 'DURUM')].isin(s_d)]
                        if s_sku: f_df = f_df[f_df.index.get_level_values('malzeme no').isin(s_sku)]
                        
                        t1, t2 = ilk_tarih, son_tarih
                        if not f_df.empty and ('Stokta Bulunan', t1) in f_df.columns and ('Stokta Bulunan', t2) in f_df.columns:
                            total_idx = pd.MultiIndex.from_tuples([('GENEL TOPLAM', '-', '-')], names=f_df.index.names)
                            tr = pd.DataFrame(index=total_idx, columns=f_df.columns)
                            tr[('Stokta Bulunan', t1)], tr[('Stokta Bulunan', t2)] = f_df[('Stokta Bulunan', t1)].sum(), f_df[('Stokta Bulunan', t2)].sum()
                            tr[('Analiz', 'Fark_Adet')], tr[('Analiz', 'Güncel_Tutar_TL')] = f_df[('Analiz', 'Fark_Adet')].sum(), f_df[('Analiz', 'Güncel_Tutar_TL')].sum()
                            f_with_t = pd.concat([f_df, tr])
                            
                            stok_cols = [('Stokta Bulunan', d) for d in benzersiz_tarihler if ('Stokta Bulunan', d) in f_with_t.columns]
                            analiz_cols = [c for c in f_with_t.columns if c[0] == 'Analiz']
                            f_with_t = f_with_t[stok_cols + analiz_cols]
                            
                            m_k, m_b = f_df[('Analiz', 'Güncel_Tutar_TL')].max(), f_df[('Analiz', 'Güncel_Tutar_TL')].min()
                            def lts(row):
                                styles = []
                                if row.name[0] == 'GENEL TOPLAM': return ['background-color: #2c3e50; color: white; font-weight: bold;' for _ in row.index]
                                tutar, durum = row[('Analiz', 'Güncel_Tutar_TL')], row[('Analiz', 'DURUM')]
                                for col in row.index:
                                    if col[0] == 'Stokta Bulunan' and col[1] == t1: styles.append('background-color: #f1f2f6; color: #7f8c8d;')
                                    elif col[0] == 'Stokta Bulunan' and col[1] == t2: styles.append('font-weight: bold;')
                                    elif col[0] == 'Analiz':
                                        if durum == 'EŞİTLENDİ': styles.append('background-color: #d6eaf8; color: #1b4f72; font-weight: bold;')
                                        elif tutar > 0:
                                            a = 0.1 + (0.4 * (tutar / m_k)) if m_k > 0 else 0.2
                                            styles.append(f'background-color: rgba(231, 76, 60, {a}); color: #7b241c; font-weight: bold;')
                                        elif tutar < 0:
                                            a = 0.1 + (0.4 * (tutar / m_b)) if m_b < 0 else 0.2
                                            styles.append(f'background-color: rgba(46, 204, 113, {a}); color: #145a32; font-weight: bold;')
                                        else: styles.append('')
                                    else: styles.append('')
                                return styles
                            st.dataframe(f_with_t.style.apply(lts, axis=1).format({('Stokta Bulunan', t1): "{:.0f}", ('Stokta Bulunan', t2): "{:.0f}", ('Analiz', 'Fark_Adet'): "{:.0f}", ('Analiz', 'Güncel_Tutar_TL'): format_money}), use_container_width=True)

            # --- TAB 5: 0020 EŞİTLEME ANALİZİ YENİ SEKMESİ ---
            with tab5:
                st.markdown("#### 🏢 0020 Deposu Eşitleme ve Nötrleme Analizi")
                st.info("💡 Buraya yüklediğiniz dosyalar ana ekranı ETKİLEMEZ. Sadece 0020 deposunun diğer depolarla olan net stok eşitliğini hesaplamak için özel bir alandır.")
                
                col_up1, col_up2 = st.columns(2)
                file_0020 = col_up1.file_uploader("1️⃣ Ana Depo (0020) Dosyasını Yükleyin", type=['xlsx'], key="up_0020")
                files_other = col_up2.file_uploader("2️⃣ Diğer Depo Dosyalarını Yükleyin (Çoklu Seçim)", type=['xlsx'], accept_multiple_files=True, key="up_other")
                
                if file_0020 and files_other:
                    with st.spinner("0020 Eşitlemesi Hesaplanıyor..."):
                        
                        # 1. 0020 Dosyasını İşle
                        df_0020 = pd.read_excel(file_0020, header=0)
                        df_0020.columns = df_0020.columns.astype(str).str.strip()
                        df_0020['malzeme no'] = df_0020['malzeme no'].astype(str)
                        df_0020['Stokta Bulunan'] = pd.to_numeric(df_0020['Stokta Bulunan'], errors='coerce').fillna(0)
                        df_0020['Toplam Fiyat'] = pd.to_numeric(df_0020['Toplam Fiyat'], errors='coerce').fillna(0)
                        
                        # Doğru finansal eşitleme için Birim Fiyatı çekiyoruz
                        df_0020['Birim_Fiyat_Hesap'] = df_0020.apply(lambda r: abs(r['Toplam Fiyat']) / abs(r['Stokta Bulunan']) if r['Stokta Bulunan'] != 0 else 0, axis=1)
                        
                        base_0020 = df_0020.groupby(['malzeme no', 'Malzeme Tanımı']).agg(
                            Adet_0020=('Stokta Bulunan', 'sum'),
                            Birim_Fiyat=('Birim_Fiyat_Hesap', 'max')
                        ).reset_index()
                        
                        # 2. Diğer Depo Dosyalarını İşle
                        liste_other = []
                        for f in files_other:
                            tmp = pd.read_excel(f, header=0)
                            tmp.columns = tmp.columns.astype(str).str.strip()
                            tmp['malzeme no'] = tmp['malzeme no'].astype(str)
                            tmp['Stokta Bulunan'] = pd.to_numeric(tmp['Stokta Bulunan'], errors='coerce').fillna(0)
                            tmp['Toplam Fiyat'] = pd.to_numeric(tmp['Toplam Fiyat'], errors='coerce').fillna(0)
                            tmp['Birim_Fiyat_Hesap'] = tmp.apply(lambda r: abs(r['Toplam Fiyat']) / abs(r['Stokta Bulunan']) if r['Stokta Bulunan'] != 0 else 0, axis=1)
                            liste_other.append(tmp)
                            
                        df_other = pd.concat(liste_other, ignore_index=True)
                        other_grouped = df_other.groupby('malzeme no').agg(
                            Adet_Diger=('Stokta Bulunan', 'sum'),
                            Birim_Fiyat_Diger=('Birim_Fiyat_Hesap', 'max'),
                            Tanimi_Diger=('Malzeme Tanımı', 'first')
                        ).reset_index()
                        
                        # 3. İki Tabloyu Birleştir (Eşitleme/Nötrleme)
                        df_eq = pd.merge(base_0020, other_grouped, on='malzeme no', how='outer')
                        df_eq['Adet_0020'] = df_eq['Adet_0020'].fillna(0)
                        df_eq['Adet_Diger'] = df_eq['Adet_Diger'].fillna(0)
                        
                        # Eksik İsimleri ve Fiyatları Tamamla
                        df_eq['Malzeme Tanımı'] = df_eq['Malzeme Tanımı'].combine_first(df_eq['Tanimi_Diger']).fillna("Bilinmiyor")
                        df_eq['Birim_Fiyat_Nihai'] = df_eq['Birim_Fiyat'].combine_first(df_eq['Birim_Fiyat_Diger']).fillna(0)
                        
                        # Kritik Formül: 0020 ile Diğer depoların toplam stok hareketlerini birbirine ekle
                        df_eq['Sonuc_Adet'] = df_eq['Adet_0020'] + df_eq['Adet_Diger']
                        
                        # Finansal Etki Hesaplamaları (Tüm Adımlar İçin)
                        def hesapla_tutar_detay(df, adet_kolon):
                            kayip_a = df[adet_kolon].apply(lambda x: x if x > 0 else 0)
                            buldum_a = df[adet_kolon].apply(lambda x: x if x < 0 else 0)
                            kayip_t = kayip_a * df['Birim_Fiyat_Nihai']
                            buldum_t = buldum_a * df['Birim_Fiyat_Nihai']
                            return kayip_a.sum(), abs(buldum_a.sum()), kayip_t.sum(), abs(buldum_t.sum())
                            
                        k_a_0, b_a_0, k_t_0, b_t_0 = hesapla_tutar_detay(df_eq, 'Adet_0020')
                        k_a_d, b_a_d, k_t_d, b_t_d = hesapla_tutar_detay(df_eq, 'Adet_Diger')
                        k_a_s, b_a_s, k_t_s, b_t_s = hesapla_tutar_detay(df_eq, 'Sonuc_Adet')
                        
                        # 4. GÖRSEL ÇIKTI (ÖZET)
                        st.markdown("<div style='background-color:#fef9e7; padding:10px; border-radius:5px; border-left: 5px solid #f1c40f;'><b>🟡 1. Ana Depo (0020) İlk Durum</b></div>", unsafe_allow_html=True)
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("🔻 Kayıp (Adet)", f"{k_a_0:,.0f}")
                        c2.metric("🔻 Kayıp (TL)", format_money(k_t_0))
                        c3.metric("🟢 Buldum (Adet)", f"{b_a_0:,.0f}")
                        c4.metric("🟢 Buldum (TL)", format_money(b_t_0))
                        
                        st.markdown("<div style='background-color:#ebf5fb; padding:10px; border-radius:5px; border-left: 5px solid #3498db; margin-top:10px;'><b>🔵 2. Diğer Depoların Nötrleme Etkisi (Toplam Net Hareket)</b></div>", unsafe_allow_html=True)
                        d1, d2, d3, d4 = st.columns(4)
                        d1.metric("🔻 Kayıp Etkisi", f"{k_a_d:,.0f}")
                        d2.metric("🔻 Kayıp Etkisi (TL)", format_money(k_t_d))
                        d3.metric("🟢 Buldum Etkisi", f"{b_a_d:,.0f}")
                        d4.metric("🟢 Buldum Etkisi (TL)", format_money(b_t_d))
                        
                        st.markdown("<div style='background-color:#e8f8f5; padding:10px; border-radius:5px; border-left: 5px solid #2ecc71; margin-top:10px;'><b>✅ 3. EŞİTLEME SONRASI 0020 GÜNCEL DURUMU</b></div>", unsafe_allow_html=True)
                        s1, s2, s3, s4 = st.columns(4)
                        s1.metric("🔻 Kalan Kayıp (Adet)", f"{k_a_s:,.0f}")
                        s2.metric("🔻 Kalan Kayıp (TL)", format_money(k_t_s))
                        s3.metric("🟢 Kalan Buldum (Adet)", f"{b_a_s:,.0f}")
                        s4.metric("🟢 Kalan Buldum (TL)", format_money(b_t_s))
                        
                        st.markdown("---")
                        
                        # 5. DETAYLI TABLO
                        st.markdown("##### 🔍 Eşitleme Detay Raporu (SKU Bazlı)")
                        
                        # Sadece hareketi olanları (0 olmayanları) göster
                        df_display = df_eq[(df_eq['Sonuc_Adet'] != 0) | (df_eq['Adet_0020'] != 0) | (df_eq['Adet_Diger'] != 0)].copy()
                        df_display['Nihai Tutar (TL)'] = df_display['Sonuc_Adet'].abs() * df_display['Birim_Fiyat_Nihai']
                        
                        df_display = df_display[['malzeme no', 'Malzeme Tanımı', 'Birim_Fiyat_Nihai', 'Adet_0020', 'Adet_Diger', 'Sonuc_Adet', 'Nihai Tutar (TL)']]
                        df_display.columns = ['Malzeme No', 'Malzeme Tanımı', 'Birim Fiyat', '0020 İlk Adet', 'Diğer Depolar Net Adet', 'EŞİTLENMİŞ SON ADET', 'Nihai Tutar (TL)']
                        df_display = df_display.sort_values(by='Nihai Tutar (TL)', ascending=False)
                        
                        def style_esitleme(row):
                            styles = ['' for _ in row.index]
                            sonuc = row['EŞİTLENMİŞ SON ADET']
                            idx = list(row.index).index('EŞİTLENMİŞ SON ADET')
                            
                            if sonuc > 0:
                                styles[idx] = 'background-color: #fadbd8; color: #922b21; font-weight: bold;'
                            elif sonuc < 0:
                                styles[idx] = 'background-color: #d5f5e3; color: #145a32; font-weight: bold;'
                            else:
                                styles[idx] = 'background-color: #d6eaf8; color: #1b4f72; font-weight: bold;'
                            return styles

                        st.dataframe(df_display.style.apply(style_esitleme, axis=1).format({
                            'Birim Fiyat': format_money,
                            '0020 İlk Adet': "{:,.0f}",
                            'Diğer Depolar Net Adet': "{:,.0f}",
                            'EŞİTLENMİŞ SON ADET': "{:,.0f}",
                            'Nihai Tutar (TL)': format_money
                        }), use_container_width=True, hide_index=True)
                        
                        # Excel İndirme
                        buffer_eq = io.BytesIO()
                        with pd.ExcelWriter(buffer_eq, engine='xlsxwriter') as writer:
                            df_display.to_excel(writer, index=False, sheet_name='0020_Esitleme_Raporu')
                        
                        st.download_button(
                            label="📥 Eşitleme Detay Raporunu İndir (Excel)",
                            data=buffer_eq.getvalue(),
                            file_name=f"0020_Esitleme_Analizi_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
                            mime="application/vnd.ms-excel",
                            use_container_width=True
                        )

            # --- EXCEL EXPORT (ANA RAPOR) ---
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                excel_dolu_mu = False
                if 'guncel_dash' in locals() and not guncel_dash.empty:
                    guncel_dash.to_excel(writer, sheet_name='Kategori_Guncel', index=False)
                    excel_dolu_mu = True
                if 'f_with_t' in locals() and not f_with_t.empty:
                    f_with_t.to_excel(writer, sheet_name='Dive_Deep_Analizi')
                    excel_dolu_mu = True
                if 'guncel_tab4_df' in locals() and not guncel_tab4_df.empty:
                    depo_liste_excel = []
                    depolar_listesi = sorted([d for d in guncel_tab4_df[depo_col].unique() if str(d).lower() != 'nan' and str(d).lower() != 'none'])
                    for d in depolar_listesi:
                        d_data = guncel_tab4_df[guncel_tab4_df[depo_col] == d]
                        sku_d = d_data.groupby(['malzeme no', 'Malzeme Tanımı', 'Ürün Tipi'])[['Kayıp_Adet', 'Kayıp_Tutar', 'Buldum_Adet', 'Buldum_Tutar']].sum().reset_index()
                        t_k = sku_d[sku_d['Kayıp_Adet'] > 0].sort_values(by='Kayıp_Tutar', ascending=False).head(20).copy()
                        if not t_k.empty:
                            t_k['Depo'] = d
                            t_k['Durum'] = 'KAYIP'
                            depo_liste_excel.append(t_k[['Depo', 'Durum', 'Ürün Tipi', 'malzeme no', 'Malzeme Tanımı', 'Kayıp_Adet', 'Kayıp_Tutar']].rename(columns={'Kayıp_Adet': 'Adet', 'Kayıp_Tutar': 'Tutar (TL)'}))
                        t_b = sku_d[sku_d['Buldum_Adet'] < 0].copy()
                        if not t_b.empty:
                            t_b['Buldum_Adet'] = t_b['Buldum_Adet'].abs()
                            t_b['Buldum_Tutar'] = t_b['Buldum_Tutar'].abs()
                            t_b = t_b.sort_values(by='Buldum_Tutar', ascending=False).head(20)
                            t_b['Depo'] = d
                            t_b['Durum'] = 'BULDUM'
                            depo_liste_excel.append(t_b[['Depo', 'Durum', 'Ürün Tipi', 'malzeme no', 'Malzeme Tanımı', 'Buldum_Adet', 'Buldum_Tutar']].rename(columns={'Buldum_Adet': 'Adet', 'Buldum_Tutar': 'Tutar (TL)'}))
                    if depo_liste_excel:
                        final_depo_excel = pd.concat(depo_liste_excel, ignore_index=True)
                        final_depo_excel.to_excel(writer, sheet_name='Depolar_Top20', index=False)
                        excel_dolu_mu = True
                if not excel_dolu_mu:
                    pd.DataFrame({'Bilgi': ['Seçili filtrelere uygun veri bulunamadı.']}).to_excel(writer, sheet_name='Bilgi', index=False)

            st.markdown("---")
            c_empty, cpdf, cex = st.columns([6, 1, 1])
            with cpdf: st.download_button("📄 Dashboard PDF İndir", data=pdf_buffer.getvalue(), file_name=f"Stok_Dashboard_{son_tarih}.pdf", use_container_width=True)
            with cex: st.download_button("📊 Tüm Analizi Excel İndir", data=excel_buffer.getvalue(), file_name=f"Stok_Detay_{son_tarih}.xlsx", use_container_width=True)

else:
    st.info("👋 Analiz raporlarını yukarıdaki mavi kesikli alana sürükleyerek başlayabilirsiniz.")
