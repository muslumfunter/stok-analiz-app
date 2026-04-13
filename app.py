import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
import plotly.graph_objects as go
import io

# 1. SAYFA AYARLARI (Geniş Ekran Modu)
st.set_page_config(page_title="Stok Analiz Dashboard", page_icon="📦", layout="wide")

st.title("📦 Operasyon Kalite - Sayım Farkı Dashboard")

# 2. YARDIMCI FONKSİYONLAR
def format_money(x):
    abs_x = abs(x)
    if abs_x >= 1_000_000:
        return f"{abs_x/1_000_000:.1f}M"
    elif abs_x >= 1_000:
        return f"{abs_x/1_000:.1f}K"
    return f"{abs_x:.0f}"

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
                        textcoords='offset points', fontsize=9, fontweight='bold')

izlenecek_urunler = ['taşınabilir bilgisayar', 'cep telefonu', 'tabletler', 'IPL cihazları']

# 3. DOSYA YÜKLEME ALANI
with st.sidebar:
    st.header("📂 Dosya Yükleme")
    st.info("Analiz edilecek Excel raporlarını seçin (En az 2 dosya)")
    uploaded_files = st.file_uploader("Excel Dosyalarını Sürükleyin", type=['xlsx'], accept_multiple_files=True)

# 4. ANALİZ VE DASHBOARD
if len(uploaded_files) < 2:
    st.warning("Grafiklerin ve fark analizinin oluşabilmesi için lütfen sol menüden en az 2 adet Excel dosyası yükleyin.")
else:
    with st.spinner("Dinamik Grafikler ve Tablolar Hazırlanıyor..."):
        # Veri Hazırlığı
        liste = []
        for f in uploaded_files:
            df = pd.read_excel(f, header=0)
            df.columns = df.columns.str.strip()
            dosya_adi = f.name.replace(".xlsx", "")
            kisa_tarih = f"{dosya_adi[:2]}/{dosya_adi[2:4]}"
            df['Rapor_Tarihi'] = kisa_tarih
            liste.append(df)
        
        df_master = pd.concat(liste, ignore_index=True).sort_values(by='Rapor_Tarihi')
        
        # BRÜT KAYIP VE BULDUM HESAPLAMALARI
        df_master['Kayıp_Adet'] = df_master['Stokta Bulunan'].apply(lambda x: x if x > 0 else 0)
        df_master['Buldum_Adet'] = df_master['Stokta Bulunan'].apply(lambda x: x if x < 0 else 0)
        
        # Tutarın yönünü adete göre garantiye alıyoruz
        df_master['Kayıp_Tutar'] = df_master.apply(lambda row: abs(row['Toplam Fiyat']) if row['Stokta Bulunan'] > 0 else 0, axis=1)
        df_master['Buldum_Tutar'] = df_master.apply(lambda row: -abs(row['Toplam Fiyat']) if row['Stokta Bulunan'] < 0 else 0, axis=1)
        
        son_tarih = df_master['Rapor_Tarihi'].iloc[-1]
        st.success("✅ Veriler başarıyla işlendi!")

        tab1, tab2, tab3 = st.tabs(["📈 Genel Dashboard", "🏢 Kategori Detayı", "🔍 Dive Deep (Malzeme No Bazlı)"])

        pdf_buffer = io.BytesIO()
        excel_buffer = io.BytesIO()

        with PdfPages(pdf_buffer) as pdf:
            
            # --- TAB 1: ANA DASHBOARD ---
            with tab1:
                st.subheader(f"Kritik Ürün Tipleri Kayıp ve Buldum Dağılımı ({son_tarih})")
                dash_df = df_master[df_master['Ürün Tipi'].str.lower().isin([x.lower() for x in izlenecek_urunler])]
                dash_grouped = dash_df.groupby(['Ürün Tipi', 'Rapor_Tarihi'])[['Stokta Bulunan', 'Toplam Fiyat', 'Kayıp_Adet', 'Buldum_Adet', 'Kayıp_Tutar', 'Buldum_Tutar']].sum().reset_index()

                # ÇİFT YÖNLÜ (BIPOLAR) İNTERAKTİF GRAFİKLER
                cols = st.columns(4)
                for i, urun in enumerate(izlenecek_urunler):
                    urun_data = dash_grouped[dash_grouped['Ürün Tipi'].str.lower() == urun.lower()].sort_values('Rapor_Tarihi')
                    with cols[i]:
                        # Stok Adet
                        fig_m_web = go.Figure()
                        kayip_txt = urun_data['Kayıp_Adet'].apply(lambda x: f"{x:.0f}" if x != 0 else "")
                        buldum_txt = urun_data['Buldum_Adet'].apply(lambda x: f"{x:.0f}" if x != 0 else "")
                        
                        fig_m_web.add_trace(go.Bar(x=urun_data['Rapor_Tarihi'], y=urun_data['Kayıp_Adet'], name='Kayıp', marker_color='#e74c3c', text=kayip_txt, textposition='auto'))
                        fig_m_web.add_trace(go.Bar(x=urun_data['Rapor_Tarihi'], y=urun_data['Buldum_Adet'], name='Buldum', marker_color='#2ecc71', text=buldum_txt, textposition='auto'))
                        fig_m_web.update_layout(barmode='relative', title=f"<b>{urun.upper()}</b><br>FARK ADET", margin=dict(t=50, b=0, l=0, r=0), height=250, showlegend=False)
                        st.plotly_chart(fig_m_web, use_container_width=True, key=f"stok_adet_grafik_{i}")

                        # Toplam Değer
                        fig_t_web = go.Figure()
                        k_tutar_txt = urun_data['Kayıp_Tutar'].apply(lambda x: format_money(x) if x != 0 else "")
                        b_tutar_txt = urun_data['Buldum_Tutar'].apply(lambda x: f"-{format_money(x)}" if x != 0 else "")
                        
                        fig_t_web.add_trace(go.Bar(x=urun_data['Rapor_Tarihi'], y=urun_data['Kayıp_Tutar'], name='Kayıp Tutar', marker_color='#e74c3c', text=k_tutar_txt, textposition='auto'))
                        fig_t_web.add_trace(go.Bar(x=urun_data['Rapor_Tarihi'], y=urun_data['Buldum_Tutar'], name='Buldum Tutar', marker_color='#2ecc71', text=b_tutar_txt, textposition='auto'))
                        fig_t_web.update_layout(barmode='relative', title="TOPLAM FARK DEĞERİ (TL)", margin=dict(t=30, b=0, l=0, r=0), height=250, showlegend=False)
                        st.plotly_chart(fig_t_web, use_container_width=True, key=f"toplam_deger_grafik_{i}")

                # YENİ NESİL DEĞİŞİM ÖZET TABLOSU
                st.markdown("---")
                st.subheader("📋 Değişim Özeti (Sadece Hareketi Olan Kategoriler)")
                
                ozet_pivot = dash_grouped.pivot_table(index='Ürün Tipi', columns='Rapor_Tarihi', values=['Kayıp_Adet', 'Buldum_Adet', 'Stokta Bulunan', 'Toplam Fiyat'], aggfunc='sum').fillna(0)

                degisim_df = pd.DataFrame()
                degisim_df['Ürün Tipi'] = ozet_pivot.index
                degisim_df['Kayıp Değişimi (Adet)'] = (ozet_pivot['Kayıp_Adet'].iloc[:, -1] - ozet_pivot['Kayıp_Adet'].iloc[:, 0]).values
                degisim_df['Buldum Değişimi (Adet)'] = (ozet_pivot['Buldum_Adet'].iloc[:, -1] - ozet_pivot['Buldum_Adet'].iloc[:, 0]).values
                degisim_df['Net Adet Değişimi'] = (ozet_pivot['Stokta Bulunan'].iloc[:, -1] - ozet_pivot['Stokta Bulunan'].iloc[:, 0]).values
                degisim_df['Net Tutar Değişimi (TL)'] = (ozet_pivot['Toplam Fiyat'].iloc[:, -1] - ozet_pivot['Toplam Fiyat'].iloc[:, 0]).values

                degisim_df = degisim_df[(degisim_df['Kayıp Değişimi (Adet)'] != 0) | (degisim_df['Buldum Değişimi (Adet)'] != 0) | (degisim_df['Net Adet Değişimi'] != 0)].copy()

                if degisim_df.empty:
                    st.info("💡 Seçili tarihler arasında bu kategorilerde herhangi bir stok sayım farkı hareketi (değişim) olmamıştır.")
                else:
                    st.dataframe(degisim_df.style.format({
                        'Kayıp Değişimi (Adet)': "{:,.0f}",
                        'Buldum Değişimi (Adet)': "{:,.0f}",
                        'Net Adet Değişimi': "{:,.0f}",
                        'Net Tutar Değişimi (TL)': "{:,.0f}"
                    }), use_container_width=True)

                # PDF İÇİN ARKA PLANDA ÇİZİM
                fig1, axes = plt.subplots(nrows=2, ncols=4, figsize=(22, 12))
                plt.subplots_adjust(hspace=0.4, wspace=0.3)
                for i, urun in enumerate(izlenecek_urunler):
                    urun_data = dash_grouped[dash_grouped['Ürün Tipi'].str.lower() == urun.lower()].sort_values('Rapor_Tarihi')
                    m_colors = get_colors_by_value(urun_data['Stokta Bulunan'])
                    ax_m = sns.barplot(data=urun_data, x='Rapor_Tarihi', y='Stokta Bulunan', ax=axes[0, i], palette=m_colors)
                    axes[0, i].set_title(f'{urun.upper()}\nNET FARK ADET', fontsize=11, fontweight='bold')
                    label_bars(ax_m, is_money=False)
                    
                    t_colors = get_colors_by_value(urun_data['Toplam Fiyat'])
                    ax_t = sns.barplot(data=urun_data, x='Rapor_Tarihi', y='Toplam Fiyat', ax=axes[1, i], palette=t_colors)
                    axes[1, i].set_title(f'NET FARK DEĞERİ (TL)', fontsize=11, fontweight='bold')
                    label_bars(ax_t, is_money=True)
                plt.suptitle(f'SAYIM FARKI DASHBOARD - {son_tarih}\n(Kırmızı: Kayıp | Yeşil: Buldum)', fontsize=22, fontweight='bold', y=0.98)
                pdf.savefig(fig1, bbox_inches='tight')
                plt.close(fig1)

            # --- TAB 2: KATEGORİ DETAYI ---
            with tab2:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader(f"Güncel Sayım Net Fark Top 10 (Ürün Tipi)")
                    guncel_df = df_master[df_master['Rapor_Tarihi'] == son_tarih]
                    top_10_stok_degeri = guncel_df.groupby('Buying Category Name')['Toplam Fiyat'].sum().sort_values(ascending=False).head(10)
                    
                    text_guncel = [format_money(val) for val in top_10_stok_degeri.values]
                    fig2_web = go.Figure(go.Bar(
                        x=top_10_stok_degeri.values, y=top_10_stok_degeri.index, orientation='h',
                        text=text_guncel, textposition='auto',
                        marker=dict(color=top_10_stok_degeri.values, colorscale='Reds', reversescale=False)
                    ))
                    fig2_web.update_layout(yaxis={'categoryorder':'total ascending'}, height=450, margin=dict(t=0, l=0, r=0, b=0))
                    st.plotly_chart(fig2_web, use_container_width=True)

                    fig2, ax_top = plt.subplots(figsize=(10, 8))
                    sns.barplot(x=top_10_stok_degeri.values, y=top_10_stok_degeri.index, palette='Reds_r', ax=ax_top)
                    plt.title('GÜNCEL SAYIM AÇIĞI (TL)', fontsize=14, fontweight='bold')
                    label_bars(ax_top, is_money=True)
                    pdf.savefig(fig2, bbox_inches='tight')
                    plt.close(fig2)

                with col2:
                    st.subheader("Kategori Bazlı Finansal Değişim (İlk vs Son Rapor)")
                    cat_pivot = df_master.pivot_table(index='Buying Category Name', columns='Rapor_Tarihi', values='Toplam Fiyat', aggfunc='sum').fillna(0)
                    cat_pivot['Fark'] = cat_pivot.iloc[:, -1] - cat_pivot.iloc[:, 0]
                    top_10_fark = cat_pivot.sort_values(by='Fark', key=abs, ascending=False).head(10)
                    
                    text_fark = [format_money(val) for val in top_10_fark['Fark']]
                    fark_renkler = get_colors_by_value(top_10_fark['Fark'])
                    fig3_web = go.Figure(go.Bar(
                        x=top_10_fark['Fark'], y=top_10_fark.index, orientation='h',
                        text=text_fark, textposition='auto', marker_color=fark_renkler
                    ))
                    fig3_web.update_layout(yaxis={'categoryorder':'total ascending'}, height=450, margin=dict(t=0, l=0, r=0, b=0))
                    st.plotly_chart(fig3_web, use_container_width=True)

                    fig3, ax_cat = plt.subplots(figsize=(10, 8))
                    sns.barplot(x=top_10_fark['Fark'], y=top_10_fark.index, palette=fark_renkler, ax=ax_cat)
                    plt.title('FİNANSAL DEĞİŞİM (FARK - TL)', fontsize=14, fontweight='bold')
                    plt.axvline(0, color='black', linewidth=1)
                    pdf.savefig(fig3, bbox_inches='tight')
                    plt.close(fig3)

            # --- TAB 3: DIVE DEEP (MALZEME NO BAZLI & FİLTRELİ) ---
            with tab3:
                st.subheader("Tüm Depo - Malzeme No (SKU) Bazlı Analiz")
                
                deep_df = df_master.copy()
                
                deep_pivot = deep_df.pivot_table(
                    index=['Ürün Tipi', 'malzeme no', 'Malzeme Tanımı'], 
                    columns='Rapor_Tarihi', 
                    values=['Stokta Bulunan', 'Birim Fiyat'], 
                    aggfunc={'Stokta Bulunan': 'sum', 'Birim Fiyat': 'mean'}
                ).fillna(0)
                
                deep_pivot[('Analiz', 'Fark_Adet')] = deep_pivot['Stokta Bulunan'].iloc[:, -1] - deep_pivot['Stokta Bulunan'].iloc[:, 0]
                deep_pivot[('Analiz', 'DURUM')] = deep_pivot[('Analiz', 'Fark_Adet')].apply(lambda x: "KAYIP" if x > 0 else ("BULDUM" if x < 0 else "SABİT"))
                
                gecerli_fiyat = deep_pivot['Birim Fiyat'].max(axis=1)
                deep_pivot[('Analiz', 'Fark_Fiyat_TL')] = deep_pivot[('Analiz', 'Fark_Adet')] * gecerli_fiyat
                
                son_tarih_stok = deep_pivot['Stokta Bulunan'].iloc[:, -1]
                degisim_farki = deep_pivot[('Analiz', 'Fark_Adet')]
                
                deep_final = deep_pivot[(son_tarih_stok != 0) | (degisim_farki != 0)].sort_values(by=[('Analiz', 'Fark_Fiyat_TL')], ascending=False)
                
                if deep_final.empty:
                    st.info("💡 Seçili tarihler arasında hareket gören veya güncelde açığı bulunan bir SKU kalmamıştır.")
                    filtered_df = deep_final
                else:
                    # --- YENİ EKLENEN FİLTRELEME ALANI ---
                    col_filt1, col_filt2 = st.columns(2)
                    
                    # 1. Durum Filtresi
                    mevcut_durumlar = deep_final[('Analiz', 'DURUM')].unique().tolist()
                    secilen_durumlar = col_filt1.multiselect("📌 Durum Filtresi (Kayıp/Buldum/Sabit):", options=mevcut_durumlar, default=mevcut_durumlar)
                    
                    # 2. Malzeme No Filtresi
                    mevcut_skular = deep_final.index.get_level_values('malzeme no').unique().tolist()
                    secilen_skular = col_filt2.multiselect("🔍 Malzeme No (SKU) Ara:", options=mevcut_skular, placeholder="Tümünü görmek için burayı boş bırakın...")
                    
                    # Filtreleri Tabloya Uygulama
                    filtered_df = deep_final.copy()
                    
                    if secilen_durumlar:
                        filtered_df = filtered_df[filtered_df[('Analiz', 'DURUM')].isin(secilen_durumlar)]
                    else:
                        filtered_df = filtered_df.iloc[0:0] # Hiçbir şey seçilmezse tabloyu boşaltır
                        
                    if secilen_skular:
                        filtered_df = filtered_df[filtered_df.index.get_level_values('malzeme no').isin(secilen_skular)]
                    
                    # Filtrelenmiş tabloyu göster
                    st.dataframe(filtered_df.style.format({('Analiz', 'Fark_Fiyat_TL'): format_money}), use_container_width=True)

                # Excel indirme bağlantısı da filtrelenmiş dataframe'i baz alsın
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    filtered_df.to_excel(writer, sheet_name='MalzemeNo_Fark_Analizi')
                    top_10_fark.to_excel(writer, sheet_name='Kategori_Ozeti')
                    degisim_df.to_excel(writer, sheet_name='Genel_Degisim_Ozeti', index=False)

        # --- İNDİRME BUTONLARI ---
        st.markdown("---")
        st.header("📥 Raporları İndir")
        col_pdf, col_excel = st.columns(2)
        with col_pdf:
            st.download_button("📄 PDF Raporunu İndir", data=pdf_buffer.getvalue(), file_name=f"Stok_Dashboard_Yatay_{son_tarih.replace('/', '')}.pdf", mime="application/pdf", use_container_width=True)
        with col_excel:
            st.download_button("📊 Excel Dive Deep İndir", data=excel_buffer.getvalue(), file_name=f"Stok_Dive_Deep_{son_tarih.replace('/', '')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
