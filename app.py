import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
import io

# 1. SAYFA AYARLARI (Geniş Ekran Modu)
st.set_page_config(page_title="Stok Analiz Dashboard", page_icon="📦", layout="wide")

st.title("📦 Operasyon Kalite - Stok Analiz Dashboard")
st.markdown("Ekip arkadaşlarınızla paylaşabileceğiniz interaktif stok takip ve analiz aracı.")

# 2. YARDIMCI FONKSİYONLAR
def format_money(x):
    abs_x = abs(x)
    if abs_x >= 1_000_000:
        return f"{x/1_000_000:.1f}M"
    elif abs_x >= 1_000:
        return f"{x/1_000:.1f}K"
    return f"{x:.0f}"

def get_colors(data, column):
    colors = ['#95a5a6'] 
    values = data[column].tolist()
    for i in range(1, len(values)):
        if values[i] > values[i-1]: colors.append('#e74c3c') # Artış: Kırmızı
        elif values[i] < values[i-1]: colors.append('#2ecc71') # Azalış: Yeşil
        else: colors.append('#95a5a6')
    return colors

def label_bars(ax, is_money=False):
    for p in ax.patches:
        val = p.get_height()
        if val != 0:
            label = format_money(val) if is_money else f"{val:.0f}"
            ax.annotate(label, 
                        (p.get_x() + p.get_width() / 2., val), 
                        ha='center', va='center', xytext=(0, 9), 
                        textcoords='offset points', fontsize=9, fontweight='bold')

izlenecek_urunler = ['cep telefonu', 'taşınabilir bilgisayar', 'tabletler', 'IPL cihazları']

# 3. DOSYA YÜKLEME ALANI (Kenar Çubuğu)
with st.sidebar:
    st.header("📂 Dosya Yükleme")
    st.info("Analiz edilecek Excel raporlarını seçin (En az 2 dosya)")
    uploaded_files = st.file_uploader("Excel Dosyalarını Sürükleyin", type=['xlsx'], accept_multiple_files=True)

# 4. ANALİZ VE DASHBOARD ÇİZİMİ
if len(uploaded_files) < 2:
    st.warning("Grafiklerin ve fark analizinin oluşabilmesi için lütfen sol menüden en az 2 adet Excel dosyası yükleyin.")
else:
    with st.spinner("Veriler işleniyor ve Dashboard hazırlanıyor..."):
        # Verileri Birleştirme
        liste = []
        for f in uploaded_files:
            df = pd.read_excel(f, header=0)
            df.columns = df.columns.str.strip()
            
            dosya_adi = f.name.replace(".xlsx", "")
            kisa_tarih = f"{dosya_adi[:2]}/{dosya_adi[2:4]}"
            df['Rapor_Tarihi'] = kisa_tarih
            liste.append(df)
        
        df_master = pd.concat(liste, ignore_index=True)
        df_master = df_master.sort_values(by='Rapor_Tarihi')
        son_tarih = df_master['Rapor_Tarihi'].iloc[-1]

        st.success("✅ Veriler başarıyla yüklendi!")

        # --- SEKME (TAB) YAPISI ---
        tab1, tab2, tab3 = st.tabs(["📈 Genel Dashboard", "🏢 Kategori Detayı", "🔍 Dive Deep (Kayıp/Artış)"])

        pdf_buffer = io.BytesIO()
        excel_buffer = io.BytesIO()

        with PdfPages(pdf_buffer) as pdf:
            
            # --- TAB 1: ANA DASHBOARD ---
            with tab1:
                st.subheader(f"Zaman Serisi: Stok Adetleri ve Tutar Gelişimi ({son_tarih})")
                dash_df = df_master[df_master['Ürün Tipi'].str.lower().isin([x.lower() for x in izlenecek_urunler])]
                dash_grouped = dash_df.groupby(['Ürün Tipi', 'Rapor_Tarihi'])[['Stokta Bulunan', 'Toplam Fiyat']].sum().reset_index()

                fig1, axes = plt.subplots(nrows=2, ncols=4, figsize=(22, 12))
                plt.subplots_adjust(hspace=0.4, wspace=0.3)
                
                for i, urun in enumerate(izlenecek_urunler):
                    urun_data = dash_grouped[dash_grouped['Ürün Tipi'].str.lower() == urun.lower()].sort_values('Rapor_Tarihi')
                    
                    ax_m = sns.barplot(data=urun_data, x='Rapor_Tarihi', y='Stokta Bulunan', ax=axes[0, i], palette=get_colors(urun_data, 'Stokta Bulunan'))
                    axes[0, i].set_title(f'{urun.upper()}\nSTOK ADET', fontsize=11, fontweight='bold')
                    label_bars(ax_m, is_money=False)
                    
                    ax_t = sns.barplot(data=urun_data, x='Rapor_Tarihi', y='Toplam Fiyat', ax=axes[1, i], palette=get_colors(urun_data, 'Toplam Fiyat'))
                    axes[1, i].set_title(f'TOPLAM DEĞER (TL)', fontsize=11, fontweight='bold')
                    label_bars(ax_t, is_money=True)
                
                plt.suptitle(f'STOK ANALİZ DASHBOARD (Kırmızı: Artış | Yeşil: Azalış)', fontsize=22, fontweight='bold', y=0.98)
                st.pyplot(fig1)
                pdf.savefig(fig1, bbox_inches='tight')

            # --- TAB 2: KATEGORİ DETAYI ---
            with tab2:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader(f"Güncel Stok Değeri En Yüksek İlk 10 Kategori")
                    guncel_df = df_master[df_master['Rapor_Tarihi'] == son_tarih]
                    top_10_stok_degeri = guncel_df.groupby('Buying Category Name')['Toplam Fiyat'].sum().sort_values(ascending=False).head(10)
                    
                    fig2, ax_top = plt.subplots(figsize=(10, 8))
                    sns.barplot(x=top_10_stok_degeri.values, y=top_10_stok_degeri.index, palette='Blues_r', ax=ax_top)
                    plt.title('GÜNCEL STOK DEĞERİ (TL)', fontsize=14, fontweight='bold')
                    label_bars(ax_top, is_money=True)
                    st.pyplot(fig2)
                    pdf.savefig(fig2, bbox_inches='tight')

                with col2:
                    st.subheader("Kategori Bazlı Finansal Değişim (İlk vs Son Rapor)")
                    cat_pivot = df_master.pivot_table(index='Buying Category Name', columns='Rapor_Tarihi', values='Toplam Fiyat', aggfunc='sum').fillna(0)
                    cat_pivot['Fark'] = cat_pivot.iloc[:, -1] - cat_pivot.iloc[:, 0]
                    top_10_fark = cat_pivot.sort_values(by='Fark', key=abs, ascending=False).head(10)
                    
                    fig3, ax_cat = plt.subplots(figsize=(10, 8))
                    cat_colors = ['#e74c3c' if x > 0 else '#2ecc71' for x in top_10_fark['Fark']]
                    sns.barplot(x=top_10_fark['Fark'], y=top_10_fark.index, palette=cat_colors, ax=ax_cat)
                    plt.title('FİNANSAL DEĞİŞİM (FARK - TL)', fontsize=14, fontweight='bold')
                    plt.axvline(0, color='black', linewidth=1)
                    st.pyplot(fig3)
                    pdf.savefig(fig3, bbox_inches='tight')

            # --- TAB 3: DIVE DEEP ---
            with tab3:
                st.subheader("Malzeme Bazlı Artış / Azalma Analizi")
                top_10_isimler = top_10_fark.index.tolist()
                deep_df = df_master[df_master['Buying Category Name'].isin(top_10_isimler)]
                deep_pivot = deep_df.pivot_table(index=['Buying Category Name', 'Ürün Tipi', 'Malzeme Tanımı'], columns='Rapor_Tarihi', values=['Stokta Bulunan', 'Birim Fiyat'], aggfunc={'Stokta Bulunan': 'sum', 'Birim Fiyat': 'mean'}).fillna(0)
                
                deep_pivot[('Analiz', 'Stok_Degisim')] = deep_pivot['Stokta Bulunan'].iloc[:, -1] - deep_pivot['Stokta Bulunan'].iloc[:, 0]
                deep_pivot[('Analiz', 'DURUM')] = deep_pivot[('Analiz', 'Stok_Degisim')].apply(lambda x: "ARTIS" if x > 0 else "AZALMA")
                deep_pivot[('Analiz', 'Fark_Fiyat_TL')] = deep_pivot[('Analiz', 'Stok_Degisim')] * deep_pivot['Birim Fiyat'].iloc[:, -1]
                deep_final = deep_pivot[deep_pivot[('Analiz', 'Stok_Degisim')] != 0].sort_values(by=[('Analiz', 'Fark_Fiyat_TL')], ascending=False)
                
                st.dataframe(deep_final.style.format({('Analiz', 'Fark_Fiyat_TL'): format_money}), use_container_width=True)

                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    deep_final.to_excel(writer, sheet_name='Fark_Analizi')
                    top_10_fark.to_excel(writer, sheet_name='Kategori_Ozeti')

        # --- İNDİRME BUTONLARI ---
        st.markdown("---")
        st.header("📥 Raporları İndir")
        col_pdf, col_excel = st.columns(2)
        
        with col_pdf:
            st.download_button(
                label="📄 PDF Raporunu İndir (Yatay Dashboard)",
                data=pdf_buffer.getvalue(),
                file_name=f"Stok_Dashboard_Yatay_{son_tarih.replace('/', '')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            
        with col_excel:
            st.download_button(
                label="📊 Excel Dive Deep Raporunu İndir",
                data=excel_buffer.getvalue(),
                file_name=f"Stok_Dive_Deep_{son_tarih.replace('/', '')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
