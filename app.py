import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
import plotly.graph_objects as go
import io
import requests
import json

# 1. SAYFA AYARLARI (Geniş Ekran Modu)
st.set_page_config(page_title="Stok Analiz Dashboard", page_icon="📦", layout="wide")

# ==========================================
# 🎨 ULTRA KOMPAKT TASARIM (CSS OPTİMİZASYONU)
# ==========================================
st.markdown("""
    <style>
    /* En üstteki boşluğu ve Streamlit header'ını tamamen yok et */
    header { display: none !important; }
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; padding-left: 1.5rem !important; padding-right: 1.5rem !important; }
    
    /* Başlık ve çizgi boşluklarını sıfırla */
    h1, h2, h3 { margin-top: 0rem !important; margin-bottom: 0.2rem !important; padding-top: 0rem !important; padding-bottom: 0rem !important; }
    hr { margin-top: 0.2rem !important; margin-bottom: 0.2rem !important; border-top: 1px solid #d1d8e0;}
    
    /* Metrik Rakamlarını Küçült */
    div[data-testid="metric-container"] { padding-top: 0rem !important; padding-bottom: 0rem !important; }
    div[data-testid="stMetricValue"] > div { font-size: 1.4rem !important; font-weight: bold; }
    div[data-testid="stMetricLabel"] > label { font-size: 0.8rem !important; margin-bottom: -0.2rem !important;}
    
    /* Çoklu Seçim (Filtre) kutusunu daralt */
    .stMultiSelect { margin-bottom: -1rem !important; }
    div[data-baseweb="select"] > div { min-height: 30px !important; }
    
    /* Tab boşluklarını daralt */
    .stTabs { margin-top: -0.5rem !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] { height: 35px; padding: 0px 10px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("### 📦 Operasyon Kalite - Sayım Farkı Dashboard")

# ==========================================
# 🔔 SLACK BOT AYARLARI
# ==========================================
slack_bildirim_gidecek_urunler = ['taşınabilir bilgisayar', 'cep telefonu'] 
SLACK_WEBHOOK_URL = "" 

def slack_bildirimi_gonder(mesaj):
    if not SLACK_WEBHOOK_URL or SLACK_WEBHOOK_URL == "": return 
    try:
        payload = {"text": mesaj}
        requests.post(SLACK_WEBHOOK_URL, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
    except Exception as e: print(f"Slack hatası: {e}")

# 2. YARDIMCI FONKSİYONLAR
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

# 3. YATAY VE ULTRA KOMPAKT DOSYA YÜKLEME
col_info, col_upload = st.columns([1.5, 3])
with col_info: 
    st.caption("💡 Karşılaştırma için en az 2 rapor yükleyin (Örn: 15_DepoA.xlsx, 16_DepoA.xlsx)")
with col_upload: 
    uploaded_files = st.file_uploader("", type=['xlsx'], accept_multiple_files=True, label_visibility="collapsed")

# 4. ANALİZ VE DASHBOARD
if len(uploaded_files) < 2:
    st.warning("👈 Analiz için en az 2 adet Excel dosyasını yukarıdaki alana yükleyin.")
else:
    with st.spinner("Veriler işleniyor..."):
        liste = []
        for f in uploaded_files:
            df = pd.read_excel(f, header=0)
            df.columns = df.columns.str.strip()
            kisa_tarih = f.name.replace(".xlsx", "")[:2]
            df['Rapor_Tarihi'] = kisa_tarih
            liste.append(df)
        
        df_master = pd.concat(liste, ignore_index=True).sort_values(by='Rapor_Tarihi')
        
        df_master['Kayıp_Adet'] = df_master['Stokta Bulunan'].apply(lambda x: x if x > 0 else 0)
        df_master['Buldum_Adet'] = df_master['Stokta Bulunan'].apply(lambda x: x if x < 0 else 0)
        df_master['Kayıp_Tutar'] = df_master.apply(lambda row: abs(row['Toplam Fiyat']) if row['Stokta Bulunan'] > 0 else 0, axis=1)
        df_master['Buldum_Tutar'] = df_master.apply(lambda row: -abs(row['Toplam Fiyat']) if row['Stokta Bulunan'] < 0 else 0, axis=1)
        son_tarih = df_master['Rapor_Tarihi'].iloc[-1]
        
        depo_col = next((c for c in df_master.columns if any(x in c.lower() for x in ['depo', 'plant', 'tesis', 'lokasyon'])), None)
        if depo_col:
            df_master[depo_col] = df_master[depo_col].astype(str).str.replace(r'\.0$', '', regex=True)
            mevcut_depolar = sorted(df_master[depo_col].unique().tolist())
            secilen_depolar = st.multiselect("🏢 **Global Depo Filtresi:**", options=mevcut_depolar, default=mevcut_depolar)
            aktif_df = df_master[df_master[depo_col].isin(secilen_depolar)].copy() if secilen_depolar else df_master.iloc[0:0].copy()
        else:
            aktif_df = df_master.copy()

        if aktif_df.empty:
            st.warning("⚠️ Lütfen en az bir depo seçin.")
        else:
            tab1, tab2, tab3 = st.tabs(["📈 Genel Dashboard", "🏢 Kategori Detayı", "🔍 Dive Deep"])
            pdf_buffer = io.BytesIO()
            excel_buffer = io.BytesIO()

            with PdfPages(pdf_buffer) as pdf:
                with tab1:
                    guncel_master_df = aktif_df[aktif_df['Rapor_Tarihi'] == son_tarih]
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(f"🔻 Toplam Kayıp (Adet) - Gün {son_tarih}", f"{guncel_master_df['Kayıp_Adet'].sum():,.0f}")
                    c2.metric(f"🔻 Toplam Kayıp (TL)", format_money(guncel_master_df['Kayıp_Tutar'].sum()))
                    c3.metric(f"🟢 Toplam Buldum (Adet)", f"{abs(guncel_master_df['Buldum_Adet'].sum()):,.0f}")
                    c4.metric(f"🟢 Toplam Buldum (TL)", format_money(abs(guncel_master_df['Buldum_Tutar'].sum())))
                    
                    # --- DÜZELTİLMİŞ YAN YANA DEPO ETİKETLERİ ---
                    if depo_col:
                        depo_ozet = guncel_master_df.groupby(depo_col)[['Kayıp_Adet', 'Kayıp_Tutar', 'Buldum_Adet', 'Buldum_Tutar']].sum().reset_index()
                        html_etiketler = "<div style='display:flex; flex-wrap:wrap; gap:8px; margin-top:5px; margin-bottom:5px;'>"
                        for _, row in depo_ozet.iterrows():
                            d_kayip_a = row['Kayıp_Adet']
                            d_kayip_t = format_money(row['Kayıp_Tutar'])
                            d_buldum_a = abs(row['Buldum_Adet'])
                            d_buldum_t = format_money(abs(row['Buldum_Tutar']))
                            
                            # Tüm HTML kodunu girinti (indentation) kullanmadan tek satıra aldım ki kod bloğuna dönüşmesin!
                            html_etiketler += f"<div style='background-color:#ffffff; border: 1px solid #d1d8e0; border-radius: 4px; padding: 4px 10px; font-size:12px; color:#2c3e50; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'><b>🏢 {row[depo_col]}</b> &nbsp;|&nbsp; <span style='color:#c0392b;'>🔻 K: <b>{d_kayip_a:,.0f}</b> <span style='font-size:10px;'>({d_kayip_t})</span></span> &nbsp;|&nbsp; <span style='color:#1e8449;'>🟢 B: <b>{d_buldum_a:,.0f}</b> <span style='font-size:10px;'>({d_buldum_t})</span></span></div>"
                        
                        html_etiketler += "</div>"
                        st.markdown(html_etiketler, unsafe_allow_html=True)
                    # ---------------------------------------------

                    st.markdown("<hr style='margin: 0.2rem 0 !important;'>", unsafe_allow_html=True)

                    dash_df = aktif_df[aktif_df['Ürün Tipi'].str.lower().isin([x.lower() for x in izlenecek_urunler])]
                    dash_grouped = dash_df.groupby(['Ürün Tipi', 'Rapor_Tarihi'])[['Stokta Bulunan', 'Toplam Fiyat', 'Kayıp_Adet', 'Buldum_Adet', 'Kayıp_Tutar', 'Buldum_Tutar']].sum().reset_index()
                    
                    cols = st.columns(4)
                    for i, urun in enumerate(izlenecek_urunler):
                        u_data = dash_grouped[dash_grouped['Ürün Tipi'].str.lower() == urun.lower()].sort_values('Rapor_Tarihi')
                        with cols[i]:
                            f_m = go.Figure()
                            f_m.add_trace(go.Bar(x=u_data['Rapor_Tarihi'], y=u_data['Kayıp_Adet'], name='Kayıp', marker_color='#e74c3c', text=u_data['Kayıp_Adet'].apply(lambda x: f"{x:.0f}" if x != 0 else ""), textposition='auto', textfont=dict(size=9)))
                            f_m.add_trace(go.Bar(x=u_data['Rapor_Tarihi'], y=u_data['Buldum_Adet'], name='Buldum', marker_color='#2ecc71', text=u_data['Buldum_Adet'].apply(lambda x: f"{x:.0f}" if x != 0 else ""), textposition='auto', textfont=dict(size=9)))
                            f_m.update_layout(barmode='relative', title=f"<b>{urun.upper()}</b><br><span style='font-size:10px;'>FARK ADET</span>", margin=dict(t=35, b=0, l=0, r=0), height=140, showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#2c3e50', size=10))
                            f_m.update_xaxes(visible=False)
                            st.plotly_chart(f_m, use_container_width=True, key=f"s_a_{i}")
                            
                            f_t = go.Figure()
                            f_t.add_trace(go.Bar(x=u_data['Rapor_Tarihi'], y=u_data['Kayıp_Tutar'], name='Kayıp T', marker_color='#e74c3c', text=u_data['Kayıp_Tutar'].apply(lambda x: format_money(x) if x != 0 else ""), textposition='auto', textfont=dict(size=9)))
                            f_t.add_trace(go.Bar(x=u_data['Rapor_Tarihi'], y=u_data['Buldum_Tutar'], name='Buldum T', marker_color='#2ecc71', text=u_data['Buldum_Tutar'].apply(lambda x: format_money(x) if x != 0 else ""), textposition='auto', textfont=dict(size=9)))
                            f_t.update_layout(barmode='relative', title="<span style='font-size:10px;'>TOPLAM FARK (TL)</span>", margin=dict(t=20, b=0, l=0, r=0), height=140, showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#2c3e50', size=10))
                            f_t.update_xaxes(title_text="Gün", title_font=dict(size=9), tickfont=dict(size=9))
                            st.plotly_chart(f_t, use_container_width=True, key=f"t_d_{i}")

                    with st.expander("📋 Kategori Değişim Özeti Tablosu (Görüntülemek için tıklayın)", expanded=False):
                        ozet_pivot = dash_grouped.pivot_table(index='Ürün Tipi', columns='Rapor_Tarihi', values=['Kayıp_Adet', 'Buldum_Adet', 'Stokta Bulunan', 'Toplam Fiyat'], aggfunc='sum').fillna(0)
                        degisim_df = pd.DataFrame()
                        if not ozet_pivot.empty and 'Kayıp_Adet' in ozet_pivot:
                            degisim_df['Ürün Tipi'] = ozet_pivot.index
                            degisim_df['Kayıp Değişimi (Adet)'] = (ozet_pivot['Kayıp_Adet'].iloc[:, -1] - ozet_pivot['Kayıp_Adet'].iloc[:, 0]).values
                            degisim_df['Buldum Değişimi (Adet)'] = (ozet_pivot['Buldum_Adet'].iloc[:, -1] - ozet_pivot['Buldum_Adet'].iloc[:, 0]).values
                            degisim_df['Net Adet Değişimi'] = (ozet_pivot['Stokta Bulunan'].iloc[:, -1] - ozet_pivot['Stokta Bulunan'].iloc[:, 0]).values
                            degisim_df['Net Tutar Değişimi (TL)'] = (ozet_pivot['Toplam Fiyat'].iloc[:, -1] - ozet_pivot['Toplam Fiyat'].iloc[:, 0]).values
                            degisim_df = degisim_df[(degisim_df['Kayıp Değişimi (Adet)'] != 0) | (degisim_df['Buldum Değişimi (Adet)'] != 0) | (degisim_df['Net Adet Değişimi'] != 0)].copy()

                        if not degisim_df.empty and SLACK_WEBHOOK_URL != "":
                            kritik_degisimler = degisim_df[degisim_df['Ürün Tipi'].str.lower().isin([u.lower() for u in slack_bildirim_gidecek_urunler])]
                            if not kritik_degisimler.empty:
                                mesaj_icerigi = "*🚨 KRİTİK ÜRÜN STOK ALARMI!*\n"
                                for _, row in kritik_degisimler.iterrows():
                                    urun = row['Ürün Tipi'].upper()
                                    net_degisim = row['Net Adet Değişimi']
                                    if net_degisim > 0: mesaj_icerigi += f"🔻 *{urun}:* {net_degisim:.0f} Adet YENİ KAYIP\n"
                                    elif net_degisim < 0: mesaj_icerigi += f"🟢 *{urun}:* {abs(net_degisim):.0f} Adet BULDUM\n"
                                slack_bildirimi_gonder(mesaj_icerigi)

                        if degisim_df.empty: st.info("Hareketi olan kategori bulunamadı.")
                        else: st.dataframe(degisim_df.style.format({'Kayıp Değişimi (Adet)': "{:,.0f}", 'Buldum Değişimi (Adet)': "{:,.0f}", 'Net Adet Değişimi': "{:,.0f}", 'Net Tutar Değişimi (TL)': "{:,.0f}"}), use_container_width=True, hide_index=True)

                    fig1, axes = plt.subplots(nrows=2, ncols=4, figsize=(16, 8))
                    plt.subplots_adjust(hspace=0.4, wspace=0.3)
                    fig1.patch.set_facecolor('#f4f6f9')
                    for i, urun in enumerate(izlenecek_urunler):
                        urun_data = dash_grouped[dash_grouped['Ürün Tipi'].str.lower() == urun.lower()].sort_values('Rapor_Tarihi')
                        if not urun_data.empty: 
                            m_colors = get_colors_by_value(urun_data['Stokta Bulunan'])
                            ax_m = sns.barplot(data=urun_data, x='Rapor_Tarihi', y='Stokta Bulunan', ax=axes[0, i], palette=m_colors)
                            axes[0, i].set_title(f'{urun.upper()}\nNET FARK ADET', fontsize=10, fontweight='bold', color='#2c3e50')
                            axes[0, i].tick_params(colors='#2c3e50', labelsize=8)
                            axes[0, i].set_facecolor('#f4f6f9')
                            axes[0, i].set_xlabel("Gün", fontsize=8)
                            label_bars(ax_m, is_money=False)
                            
                            t_colors = get_colors_by_value(urun_data['Toplam Fiyat'])
                            ax_t = sns.barplot(data=urun_data, x='Rapor_Tarihi', y='Toplam Fiyat', ax=axes[1, i], palette=t_colors)
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

                with tab2:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**🔻 Güncel Kayıp En Yüksek İlk 10**")
                        t10_s = guncel_master_df.groupby('Buying Category Name')['Toplam Fiyat'].sum().sort_values(ascending=False).head(10)
                        if not t10_s.empty:
                            f2 = go.Figure(go.Bar(x=t10_s.values, y=t10_s.index, orientation='h', marker=dict(color=t10_s.values, colorscale='Reds')))
                            f2.update_layout(yaxis={'categoryorder':'total ascending'}, height=400, margin=dict(t=0, l=0, r=0, b=0), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#2c3e50'))
                            st.plotly_chart(f2, use_container_width=True)
                    with col2:
                        st.markdown("**💸 Finansal Değişim (İlk vs Son)**")
                        cp = aktif_df.pivot_table(index='Buying Category Name', columns='Rapor_Tarihi', values='Toplam Fiyat', aggfunc='sum').fillna(0)
                        if len(cp.columns) > 1:
                            cp['Fark'] = cp.iloc[:, -1] - cp.iloc[:, 0]
                            t10_f = cp.sort_values(by='Fark', key=abs, ascending=False).head(10)
                            f3 = go.Figure(go.Bar(x=t10_f['Fark'], y=t10_f.index, orientation='h', marker_color=get_colors_by_value(t10_f['Fark'])))
                            f3.update_layout(height=400, margin=dict(t=0, l=0, r=0, b=0), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#2c3e50'))
                            st.plotly_chart(f3, use_container_width=True)

                with tab3:
                    st.markdown("**🔍 Malzeme Bazlı Analiz (SKU)**")
                    dp = aktif_df.pivot_table(index=['Ürün Tipi', 'malzeme no', 'Malzeme Tanımı'], columns='Rapor_Tarihi', values=['Stokta Bulunan', 'Birim Fiyat'], aggfunc={'Stokta Bulunan': 'sum', 'Birim Fiyat': 'mean'}).fillna(0)
                    if len(dp.columns.levels[1]) > 1:
                        dp[('Analiz', 'Fark_Adet')] = dp['Stokta Bulunan'].iloc[:, -1] - dp['Stokta Bulunan'].iloc[:, 0]
                        def b_d(r):
                            if r['Stokta Bulunan'].iloc[-1] == 0: return "EŞİTLENDİ"
                            elif r[('Analiz', 'Fark_Adet')] > 0: return "KAYIP"
                            elif r[('Analiz', 'Fark_Adet')] < 0: return "BULDUM"
                            else: return "SABİT"
                        dp[('Analiz', 'DURUM')] = dp.apply(b_d, axis=1)
                        gf = dp['Birim Fiyat'].max(axis=1)
                        dp[('Analiz', 'Güncel_Tutar_TL')] = dp['Stokta Bulunan'].iloc[:, -1] * gf
                        df_f = dp[(dp['Stokta Bulunan'].iloc[:, -1] != 0) | (dp[('Analiz', 'Fark_Adet')] != 0)].sort_values(by=[('Analiz', 'Güncel_Tutar_TL')], ascending=False)
                        if 'Birim Fiyat' in df_f.columns.get_level_values(0): df_f = df_f.drop(columns=['Birim Fiyat'])
                        
                        cf1, cf2, cf3 = st.columns(3)
                        st_i = cf1.multiselect("📊 Ürün Tipi:", options=sorted(df_f.index.get_level_values('Ürün Tipi').unique()))
                        m_d = df_f[('Analiz', 'DURUM')].unique().tolist()
                        s_d = cf2.multiselect("📌 Durum:", options=m_d, default=[d for d in ["KAYIP", "BULDUM", "EŞİTLENDİ", "SABİT"] if d in m_d])
                        s_sku = cf3.multiselect("🔍 Malzeme No:", options=df_f.index.get_level_values('malzeme no').unique())
                        
                        f_df = df_f.copy()
                        if st_i: f_df = f_df[f_df.index.get_level_values('Ürün Tipi').isin(st_i)]
                        if s_d: f_df = f_df[f_df[('Analiz', 'DURUM')].isin(s_d)]
                        if s_sku: f_df = f_df[f_df.index.get_level_values('malzeme no').isin(s_sku)]
                        
                        t1, t2 = f_df['Stokta Bulunan'].columns[0], f_df['Stokta Bulunan'].columns[-1]
                        if not f_df.empty:
                            total_idx = pd.MultiIndex.from_tuples([('GENEL TOPLAM', '-', '-')], names=f_df.index.names)
                            tr = pd.DataFrame(index=total_idx, columns=f_df.columns)
                            tr[('Stokta Bulunan', t1)], tr[('Stokta Bulunan', t2)] = f_df[('Stokta Bulunan', t1)].sum(), f_df[('Stokta Bulunan', t2)].sum()
                            tr[('Analiz', 'Fark_Adet')], tr[('Analiz', 'Güncel_Tutar_TL')] = f_df[('Analiz', 'Fark_Adet')].sum(), f_df[('Analiz', 'Güncel_Tutar_TL')].sum()
                            f_with_t = pd.concat([f_df, tr])
                            
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

            # İndirme Butonları
            c_empty, cpdf, cex = st.columns([6, 1, 1])
            with cpdf: st.download_button("📄 PDF İndir", data=pdf_buffer.getvalue(), file_name=f"Stok_Dashboard_{son_tarih}.pdf", use_container_width=True)
            with cex: 
                try: st.download_button("📊 Excel İndir", data=excel_buffer.getvalue(), file_name=f"Stok_Detay_{son_tarih}.xlsx", use_container_width=True)
                except: st.download_button("📊 Excel İndir", data=b"", file_name=f"Stok_Detay_Bos.xlsx", use_container_width=True)
