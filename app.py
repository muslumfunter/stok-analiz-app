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

st.title("📦 Operasyon Kalite - Sayım Farkı Dashboard")

# ==========================================
# 🔔 SLACK BOT AYARLARI
# ==========================================
slack_bildirim_gidecek_urunler = ['taşınabilir bilgisayar', 'cep telefonu'] # Alarm kurulacak ürünler
SLACK_WEBHOOK_URL = "" # KOPYALADIĞIN LİNKİ BURAYA YAPIŞTIR

def slack_bildirimi_gonder(mesaj):
    if not SLACK_WEBHOOK_URL or SLACK_WEBHOOK_URL == "":
        return 
    try:
        payload = {"text": mesaj}
        requests.post(SLACK_WEBHOOK_URL, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
    except Exception as e:
        print(f"Slack hatası: {e}")
# ==========================================

# 2. YARDIMCI FONKSİYONLAR
def format_money(x):
    try:
        val = float(x)
        is_negative = val < 0
        abs_x = abs(val)
        sign = "-" if is_negative else ""
        if abs_x >= 1_000_000:
            return f"{sign}{abs_x/1_000_000:.1f}M"
        elif abs_x >= 1_000:
            return f"{sign}{abs_x/1_000:.1f}K"
        return f"{sign}{abs_x:.0f}"
    except:
        return str(x)

def get_colors_by_value(values):
    return ['#e74c3c' if val > 0 else '#2ecc71' for val in values]

def label_bars(ax, is_money=False):
    for p in ax.patches:
        val = p.get_height()
        if val != 0:
            label = format_money(val) if is_money else f"{val:.0f}"
            ax.annotate(label, 
                        (p.get_x() + p.get_width() / 2., val), 
                        ha='center', va='center', xytext=(0, 9), 
                        textcoords='offset points', fontsize=9, fontweight='bold', color="#2c3e50")

izlenecek_urunler = ['taşınabilir bilgisayar', 'cep telefonu', 'tabletler', 'IPL cihazları']

# 3. DOSYA YÜKLEME ALANI
with st.sidebar:
    st.header("📂 Dosya Yükleme")
    st.info("Karşılaştırma yapılacak raporları seçin (Örn: 1504_DepoA, 1604_DepoA...)")
    uploaded_files = st.file_uploader("Excel Dosyalarını Sürükleyin", type=['xlsx'], accept_multiple_files=True)

# 4. ANALİZ VE DASHBOARD
if len(uploaded_files) < 2:
    st.info("👈 Lütfen analizin yapılabilmesi için en az 2 adet (Farklı tarihlere ait) Excel dosyasını sol menüden yükleyin.")
else:
    with st.spinner("Tüm depolar taranıyor ve dinamik tablolar hazırlanıyor..."):
        liste = []
        for f in uploaded_files:
            df = pd.read_excel(f, header=0)
            df.columns = df.columns.str.strip()
            dosya_adi = f.name.replace(".xlsx", "")
            kisa_tarih = f"{dosya_adi[:2]}/{dosya_adi[2:4]}"
            df['Rapor_Tarihi'] = kisa_tarih
            liste.append(df)
        
        df_master = pd.concat(liste, ignore_index=True).sort_values(by='Rapor_Tarihi')
        
        df_master['Kayıp_Adet'] = df_master['Stokta Bulunan'].apply(lambda x: x if x > 0 else 0)
        df_master['Buldum_Adet'] = df_master['Stokta Bulunan'].apply(lambda x: x if x < 0 else 0)
        
        df_master['Kayıp_Tutar'] = df_master.apply(lambda row: abs(row['Toplam Fiyat']) if row['Stokta Bulunan'] > 0 else 0, axis=1)
        df_master['Buldum_Tutar'] = df_master.apply(lambda row: -abs(row['Toplam Fiyat']) if row['Stokta Bulunan'] < 0 else 0, axis=1)
        
        son_tarih = df_master['Rapor_Tarihi'].iloc[-1]
        
        # --- AKILLI DEPO SÜTUNU BULUCU ---
        depo_col = next((c for c in df_master.columns if 'depo' in c.lower() or 'plant' in c.lower() or 'tesis' in c.lower() or 'lokasyon' in c.lower()), None)
        
        # --- GLOBAL DEPO FİLTRESİ ---
        st.success(f"✅ {len(uploaded_files)} adet dosya başarıyla işlendi ve birleştirildi!")
        
        if depo_col:
            mevcut_depolar = sorted(df_master[depo_col].dropna().astype(str).unique().tolist())
            st.markdown("### 🏢 Global Depo Filtresi")
            secilen_depolar = st.multiselect(
                f"Analiz edilecek depoları seçin (Boş bırakırsanız {len(mevcut_depolar)} deponun konsolide toplamını görürsünüz):", 
                options=mevcut_depolar, 
                default=mevcut_depolar
            )
            
            if secilen_depolar:
                aktif_df = df_master[df_master[depo_col].astype(str).isin(secilen_depolar)].copy()
            else:
                aktif_df = df_master.iloc[0:0].copy() 
        else:
            aktif_df = df_master.copy()
            st.info("💡 Excel dosyalarınızda 'Depo' veya 'Plant' isimli bir sütun bulunamadığı için depo ayırımı yapılamadı. Tüm veriler konsolide gösteriliyor.")

        if aktif_df.empty:
            st.warning("⚠️ Lütfen analizi görmek için yukarıdan en az bir adet depo seçimi yapınız.")
        else:
            tab1, tab2, tab3 = st.tabs(["📈 Genel Dashboard", "🏢 Kategori Detayı", "🔍 Dive Deep (Malzeme No Bazlı)"])

            pdf_buffer = io.BytesIO()
            excel_buffer = io.BytesIO()

            with PdfPages(pdf_buffer) as pdf:
                
                # --- TAB 1: ANA DASHBOARD ---
                with tab1:
                    st.subheader(f"📊 Tüm Depo Genel Durum Özeti (Güncel: {son_tarih})")
                    guncel_master_df = aktif_df[aktif_df['Rapor_Tarihi'] == son_tarih]
                    toplam_kayip_adet = guncel_master_df['Kayıp_Adet'].sum()
                    toplam_kayip_tl = guncel_master_df['Kayıp_Tutar'].sum()
                    toplam_buldum_adet = abs(guncel_master_df['Buldum_Adet'].sum()) 
                    toplam_buldum_tl = abs(guncel_master_df['Buldum_Tutar'].sum())   
                    
                    col_ozet1, col_ozet2, col_ozet3, col_ozet4 = st.columns(4)
                    col_ozet1.metric("🔻 Toplam Kayıp (Adet)", f"{toplam_kayip_adet:,.0f}")
                    col_ozet2.metric("🔻 Toplam Kayıp (TL)", format_money(toplam_kayip_tl))
                    col_ozet3.metric("🟢 Toplam Buldum (Adet)", f"{toplam_buldum_adet:,.0f}")
                    col_ozet4.metric("🟢 Toplam Buldum (TL)", format_money(toplam_buldum_tl))
                    
                    st.markdown("---")

                    st.subheader(f"D-1 vs D0 Değişim ({son_tarih})")
                    dash_df = aktif_df[aktif_df['Ürün Tipi'].str.lower().isin([x.lower() for x in izlenecek_urunler])]
                    dash_grouped = dash_df.groupby(['Ürün Tipi', 'Rapor_Tarihi'])[['Stokta Bulunan', 'Toplam Fiyat', 'Kayıp_Adet', 'Buldum_Adet', 'Kayıp_Tutar', 'Buldum_Tutar']].sum().reset_index()

                    cols = st.columns(4)
                    for i, urun in enumerate(izlenecek_urunler):
                        urun_data = dash_grouped[dash_grouped['Ürün Tipi'].str.lower() == urun.lower()].sort_values('Rapor_Tarihi')
                        with cols[i]:
                            fig_m_web = go.Figure()
                            kayip_txt = urun_data['Kayıp_Adet'].apply(lambda x: f"{x:.0f}" if x != 0 else "")
                            buldum_txt = urun_data['Buldum_Adet'].apply(lambda x: f"{x:.0f}" if x != 0 else "")
                            
                            fig_m_web.add_trace(go.Bar(x=urun_data['Rapor_Tarihi'], y=urun_data['Kayıp_Adet'], name='Kayıp', marker_color='#e74c3c', text=kayip_txt, textposition='auto'))
                            fig_m_web.add_trace(go.Bar(x=urun_data['Rapor_Tarihi'], y=urun_data['Buldum_Adet'], name='Buldum', marker_color='#2ecc71', text=buldum_txt, textposition='auto'))
                            fig_m_web.update_layout(barmode='relative', title=f"<b>{urun.upper()}</b><br>FARK ADET", margin=dict(t=50, b=0, l=0, r=0), height=250, showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#2c3e50'))
                            st.plotly_chart(fig_m_web, use_container_width=True, key=f"stok_adet_grafik_{i}")

                            fig_t_web = go.Figure()
                            k_tutar_txt = urun_data['Kayıp_Tutar'].apply(lambda x: format_money(x) if x != 0 else "")
                            b_tutar_txt = urun_data['Buldum_Tutar'].apply(lambda x: format_money(x) if x != 0 else "")
                            
                            fig_t_web.add_trace(go.Bar(x=urun_data['Rapor_Tarihi'], y=urun_data['Kayıp_Tutar'], name='Kayıp Tutar', marker_color='#e74c3c', text=k_tutar_txt, textposition='auto'))
                            fig_t_web.add_trace(go.Bar(x=urun_data['Rapor_Tarihi'], y=urun_data['Buldum_Tutar'], name='Buldum Tutar', marker_color='#2ecc71', text=b_tutar_txt, textposition='auto'))
                            fig_t_web.update_layout(barmode='relative', title="TOPLAM FARK DEĞERİ (TL)", margin=dict(t=30, b=0, l=0, r=0), height=250, showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#2c3e50'))
                            st.plotly_chart(fig_t_web, use_container_width=True, key=f"toplam_deger_grafik_{i}")

                    st.markdown("---")
                    st.subheader("📋 Değişim Özeti (Sadece Hareketi Olan Kategoriler)")
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

                    if degisim_df.empty:
                        st.info("💡 Seçili tarihler arasında bu kategorilerde herhangi bir stok sayım farkı hareketi (değişim) olmamıştır.")
                    else:
                        st.dataframe(degisim_df.style.format({'Kayıp Değişimi (Adet)': "{:,.0f}", 'Buldum Değişimi (Adet)': "{:,.0f}", 'Net Adet Değişimi': "{:,.0f}", 'Net Tutar Değişimi (TL)': "{:,.0f}"}), use_container_width=True)

                    fig1, axes = plt.subplots(nrows=2, ncols=4, figsize=(22, 12))
                    plt.subplots_adjust(hspace=0.4, wspace=0.3)
                    fig1.patch.set_facecolor('#f4f6f9')
                    for i, urun in enumerate(izlenecek_urunler):
                        urun_data = dash_grouped[dash_grouped['Ürün Tipi'].str.lower() == urun.lower()].sort_values('Rapor_Tarihi')
                        if not urun_data.empty: 
                            m_colors = get_colors_by_value(urun_data['Stokta Bulunan'])
                            ax_m = sns.barplot(data=urun_data, x='Rapor_Tarihi', y='Stokta Bulunan', ax=axes[0, i], palette=m_colors)
                            axes[0, i].set_title(f'{urun.upper()}\nNET FARK ADET', fontsize=11, fontweight='bold', color='#2c3e50')
                            axes[0, i].tick_params(colors='#2c3e50')
                            axes[0, i].set_facecolor('#f4f6f9')
                            label_bars(ax_m, is_money=False)
                            
                            t_colors = get_colors_by_value(urun_data['Toplam Fiyat'])
                            ax_t = sns.barplot(data=urun_data, x='Rapor_Tarihi', y='Toplam Fiyat', ax=axes[1, i], palette=t_colors)
                            axes[1, i].set_title(f'NET FARK DEĞERİ (TL)', fontsize=11, fontweight='bold', color='#2c3e50')
                            axes[1, i].tick_params(colors='#2c3e50')
                            axes[1, i].set_facecolor('#f4f6f9')
                            label_bars(ax_t, is_money=True)
                        else:
                            axes[0, i].set_title(f'{urun.upper()}\n(Veri Yok)', fontsize=11, fontweight='bold')
                            axes[1, i].set_title(f'(Veri Yok)', fontsize=11, fontweight='bold')
                    plt.suptitle(f'SAYIM FARKI DASHBOARD - {son_tarih}\n(Kırmızı: Kayıp | Yeşil: Buldum)', fontsize=22, fontweight='bold', color='#2c3e50', y=0.98)
                    pdf.savefig(fig1, bbox_inches='tight')
                    plt.close(fig1)

                # --- TAB 2: KATEGORİ DETAYI ---
                with tab2:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader(f"Güncel Kayıp En Yüksek İlk 10")
                        top_10_stok_degeri = guncel_master_df.groupby('Buying Category Name')['Toplam Fiyat'].sum().sort_values(ascending=False).head(10)
                        
                        if not top_10_stok_degeri.empty:
                            fig2_web = go.Figure(go.Bar(x=top_10_stok_degeri.values, y=top_10_stok_degeri.index, orientation='h', marker=dict(color=top_10_stok_degeri.values, colorscale='Reds')))
                            fig2_web.update_layout(yaxis={'categoryorder':'total ascending'}, height=450, margin=dict(t=0, l=0, r=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#2c3e50'))
                            st.plotly_chart(fig2_web, use_container_width=True)

                            fig2, ax_top = plt.subplots(figsize=(10, 8))
                            fig2.patch.set_facecolor('#f4f6f9')
                            ax_top.set_facecolor('#f4f6f9')
                            sns.barplot(x=top_10_stok_degeri.values, y=top_10_stok_degeri.index, palette='Reds_r', ax=ax_top)
                            plt.title('GÜNCEL SAYIM AÇIĞI (TL)', fontsize=14, fontweight='bold', color='#2c3e50')
                            ax_top.tick_params(colors='#2c3e50')
                            label_bars(ax_top, is_money=True)
                            pdf.savefig(fig2, bbox_inches='tight')
                            plt.close(fig2)

                    with col2:
                        st.subheader("Kategori Bazlı Finansal Değişim (İlk vs Son)")
                        cat_pivot = aktif_df.pivot_table(index='Buying Category Name', columns='Rapor_Tarihi', values='Toplam Fiyat', aggfunc='sum').fillna(0)
                        if not cat_pivot.empty and len(cat_pivot.columns) > 1:
                            cat_pivot['Fark'] = cat_pivot.iloc[:, -1] - cat_pivot.iloc[:, 0]
                            top_10_fark = cat_pivot.sort_values(by='Fark', key=abs, ascending=False).head(10)
                            top_10_fark = pd.concat([top_10_fark[top_10_fark['Fark'] <= 0].sort_values(by='Fark', ascending=False), top_10_fark[top_10_fark['Fark'] > 0].sort_values(by='Fark', ascending=True)])
                            fig3_web = go.Figure(go.Bar(x=top_10_fark['Fark'], y=top_10_fark.index, orientation='h', marker_color=get_colors_by_value(top_10_fark['Fark'])))
                            fig3_web.update_layout(height=450, margin=dict(t=0, l=0, r=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#2c3e50'))
                            st.plotly_chart(fig3_web, use_container_width=True)

                            fig3, ax_cat = plt.subplots(figsize=(10, 8))
                            fig3.patch.set_facecolor('#f4f6f9')
                            ax_cat.set_facecolor('#f4f6f9')
                            sns.barplot(x=top_10_fark['Fark'], y=top_10_fark.index, palette=get_colors_by_value(top_10_fark['Fark']), ax=ax_cat)
                            plt.title('FİNANSAL DEĞİŞİM (FARK - TL)', fontsize=14, fontweight='bold', color='#2c3e50')
                            ax_cat.tick_params(colors='#2c3e50')
                            plt.axvline(0, color='#2c3e50', linewidth=1)
                            pdf.savefig(fig3, bbox_inches='tight')
                            plt.close(fig3)

                # --- TAB 3: DIVE DEEP ---
                with tab3:
                    st.subheader("Tüm Depo - Malzeme No (SKU) Bazlı Analiz")
                    deep_df = aktif_df.copy()
                    deep_pivot = deep_df.pivot_table(index=['Ürün Tipi', 'malzeme no', 'Malzeme Tanımı'], columns='Rapor_Tarihi', values=['Stokta Bulunan', 'Birim Fiyat'], aggfunc={'Stokta Bulunan': 'sum', 'Birim Fiyat': 'mean'}).fillna(0)
                    
                    if not deep_pivot.empty and len(deep_pivot.columns.levels[1]) > 1:
                        deep_pivot[('Analiz', 'Fark_Adet')] = deep_pivot['Stokta Bulunan'].iloc[:, -1] - deep_pivot['Stokta Bulunan'].iloc[:, 0]
                        
                        def belirle_durum(row):
                            if row['Stokta Bulunan'].iloc[-1] == 0: return "EŞİTLENDİ"
                            elif row[('Analiz', 'Fark_Adet')] > 0: return "KAYIP"
                            elif row[('Analiz', 'Fark_Adet')] < 0: return "BULDUM"
                            else: return "SABİT"
                        
                        deep_pivot[('Analiz', 'DURUM')] = deep_pivot.apply(belirle_durum, axis=1)
                        gecerli_fiyat = deep_pivot['Birim Fiyat'].max(axis=1)
                        deep_pivot[('Analiz', 'Fark_Fiyat_TL')] = deep_pivot[('Analiz', 'Fark_Adet')] * gecerli_fiyat
                        deep_final = deep_pivot[(deep_pivot['Stokta Bulunan'].iloc[:, -1] != 0) | (deep_pivot[('Analiz', 'Fark_Adet')] != 0)].sort_values(by=[('Analiz', 'Fark_Fiyat_TL')], ascending=False)
                        
                        if 'Birim Fiyat' in deep_final.columns.get_level_values(0): deep_final = deep_final.drop(columns=['Birim Fiyat'])
                        
                        if deep_final.empty:
                            st.info("💡 Herhangi bir sayım farkı hareketi bulunamadı.")
                        else:
                            col_f1, col_f2, col_f3 = st.columns(3)
                            secilen_tipler = col_f1.multiselect("📊 Ürün Tipi:", options=sorted(deep_final.index.get_level_values('Ürün Tipi').unique().tolist()))
                            
                            # --- HATA ÇÖZÜMÜ BURADA EKLENDİ ---
                            mevcut_durumlar = deep_final[('Analiz', 'DURUM')].unique().tolist()
                            guvenli_varsayilanlar = [d for d in ["KAYIP", "BULDUM", "EŞİTLENDİ"] if d in mevcut_durumlar]
                            secilen_durumlar = col_f2.multiselect("📌 Durum:", options=mevcut_durumlar, default=guvenli_varsayilanlar)
                            # -----------------------------------
                            
                            secilen_skular = col_f3.multiselect("🔍 Malzeme No Ara:", options=deep_final.index.get_level_values('malzeme no').unique().tolist())
                            
                            filtered_df = deep_final.copy()
                            if secilen_tipler: filtered_df = filtered_df[filtered_df.index.get_level_values('Ürün Tipi').isin(secilen_tipler)]
                            if secilen_durumlar: filtered_df = filtered_df[filtered_df[('Analiz', 'DURUM')].isin(secilen_durumlar)]
                            if secilen_skular: filtered_df = filtered_df[filtered_df.index.get_level_values('malzeme no').isin(secilen_skular)]
                            
                            tarih1, tarih2 = filtered_df['Stokta Bulunan'].columns.tolist()[0], filtered_df['Stokta Bulunan'].columns.tolist()[-1]
                            
                            if not filtered_df.empty:
                                total_idx = pd.MultiIndex.from_tuples([('GENEL TOPLAM', '-', '-')], names=filtered_df.index.names)
                                total_row = pd.DataFrame(index=total_idx, columns=filtered_df.columns)
                                total_row[('Stokta Bulunan', tarih1)] = filtered_df[('Stokta Bulunan', tarih1)].sum()
                                total_row[('Stokta Bulunan', tarih2)] = filtered_df[('Stokta Bulunan', tarih2)].sum()
                                total_row[('Analiz', 'Fark_Adet')] = filtered_df[('Analiz', 'Fark_Adet')].sum()
                                total_row[('Analiz', 'DURUM')] = "" 
                                total_row[('Analiz', 'Fark_Fiyat_TL')] = filtered_df[('Analiz', 'Fark_Fiyat_TL')].sum()
                                df_with_total = pd.concat([filtered_df, total_row])
                            else: df_with_total = filtered_df

                            max_kayip = filtered_df[('Analiz', 'Fark_Fiyat_TL')].max() if not filtered_df.empty else 0
                            min_buldum = filtered_df[('Analiz', 'Fark_Fiyat_TL')].min() if not filtered_df.empty else 0

                            def light_theme_styling(row):
                                styles = []
                                if row.name[0] == 'GENEL TOPLAM':
                                    return ['background-color: #2c3e50; color: #ffffff; font-weight: bold; border-top: 2px solid #34495e;' for _ in row.index]
                                
                                fark = row[('Analiz', 'Fark_Fiyat_TL')]
                                durum = row[('Analiz', 'DURUM')]
                                
                                for col in row.index:
                                    if col[0] == 'Stokta Bulunan' and col[1] == tarih1: styles.append('background-color: #f1f2f6; color: #7f8c8d;')
                                    elif col[0] == 'Stokta Bulunan' and col[1] == tarih2: styles.append('background-color: #ffffff; color: #2c3e50; font-weight: bold;')
                                    elif col[0] == 'Analiz':
                                        if durum == 'EŞİTLENDİ': styles.append('background-color: #d6eaf8; color: #1b4f72; font-weight: bold;')
                                        elif fark > 0:
                                            alpha = 0.1 + (0.4 * (fark / max_kayip)) if max_kayip > 0 else 0.2
                                            styles.append(f'background-color: rgba(231, 76, 60, {alpha}); color: #7b241c; font-weight: bold;')
                                        elif fark < 0:
                                            alpha = 0.1 + (0.4 * (fark / min_buldum)) if min_buldum < 0 else 0.2
                                            styles.append(f'background-color: rgba(46, 204, 113, {alpha}); color: #145a32; font-weight: bold;')
                                        else: styles.append('background-color: #ffffff; color: #2c3e50;')
                                    else: styles.append('background-color: #ffffff; color: #2c3e50;')
                                return styles

                            st.dataframe(df_with_total.style.apply(light_theme_styling, axis=1).format({('Stokta Bulunan', tarih1): "{:.0f}", ('Stokta Bulunan', tarih2): "{:.0f}", ('Analiz', 'Fark_Adet'): "{:.0f}", ('Analiz', 'Fark_Fiyat_TL'): format_money}), use_container_width=True)

            st.markdown("---")
            st.header("📥 Raporları İndir")
            col_pdf, col_excel = st.columns(2)
            with col_pdf: st.download_button("📄 PDF Raporu", data=pdf_buffer.getvalue(), file_name=f"Stok_Dashboard_{son_tarih.replace('/', '')}.pdf", use_container_width=True)
            with col_excel: 
                try:
                    st.download_button("📊 Excel Detay", data=excel_buffer.getvalue(), file_name=f"Stok_Detay_{son_tarih.replace('/', '')}.xlsx", use_container_width=True)
                except:
                    st.download_button("📊 Excel Detay", data=b"", file_name=f"Stok_Detay_Bos.xlsx", use_container_width=True)
