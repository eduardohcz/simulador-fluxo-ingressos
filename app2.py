import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import altair as alt
from io import BytesIO
from fpdf import FPDF

st.set_page_config(page_title="Simulador de Fluxo de Ingressos", layout="centered")
st.title("🎟️ Simulador de Fluxo de Recebíveis de Ingressos")

# Inputs do usuário
total_vendas = st.number_input("Total bruto de vendas (R$)", min_value=0.0, value=100000.0, step=1000.0)
evento_data = st.date_input("Data do evento")
data_hoje = datetime.today()
dias_ate_evento = (evento_data - data_hoje.date()).days

st.markdown("### Taxas")
taxa_antecipacao_mensal = st.number_input("Taxa de antecipação mensal (%)", min_value=0.0, value=2.0, step=0.1) / 100
taxa_fluxo_mensal = st.number_input("Taxa no fluxo mensal (%)", min_value=0.0, value=1.0, step=0.1) / 100
rendimento_mensal_aplicacao = st.number_input("Rendimento mensal da aplicação (%)", min_value=0.0, value=1.05, step=0.05) / 100

st.markdown("### Distribuição das vendas por método de pagamento")
metodos = st.text_area("Insira os métodos de pagamento (1 por linha, formato: parcelas;porcentagem)",
                       value="1;10\n2;10\n3;30\n6;25\n12;25")

# Converte entrada em estrutura de dados
parcelamento_distribuicao = {}
for linha in metodos.strip().split('\n'):
    try:
        p, pct = linha.strip().split(';')
        p = int(p)
        pct = float(pct)
        parcelamento_distribuicao[p] = pct / 100
    except:
        st.error(f"Erro ao interpretar a linha: {linha}")

# Normaliza para somar 100%
total_pct = sum(parcelamento_distribuicao.values())
if total_pct > 0:
    parcelamento_distribuicao = {k: v / total_pct for k, v in parcelamento_distribuicao.items()}

# Simulação do fluxo de recebimento
def simular_fluxo():
    dados = []
    for parcelas, proporcao in parcelamento_distribuicao.items():
        valor_bruto = total_vendas * proporcao
        valor_parcela = valor_bruto / parcelas
        for i in range(1, parcelas + 1):
            dias_ate_recebimento = i * 30
            if dias_ate_recebimento <= dias_ate_evento:
                valor_liquido = valor_parcela * ((1 - taxa_fluxo_mensal) ** (dias_ate_recebimento / 30))
                dados.append({
                    'parcelas': parcelas,
                    'tipo': 'Fluxo',
                    'dias até recebimento': dias_ate_recebimento,
                    'valor bruto': valor_parcela,
                    'valor líquido': valor_liquido
                })
            else:
                meses_antecipacao = dias_ate_recebimento / 30
                valor_antecipado = valor_parcela * ((1 - taxa_antecipacao_mensal) ** meses_antecipacao)
                meses_aplicacao = dias_ate_evento / 30
                valor_aplicado = valor_antecipado * ((1 + rendimento_mensal_aplicacao) ** meses_aplicacao)
                dados.append({
                    'parcelas': parcelas,
                    'tipo': 'Antecipado',
                    'dias até recebimento': dias_ate_recebimento,
                    'valor bruto': valor_parcela,
                    'valor líquido': valor_aplicado
                })
    return pd.DataFrame(dados)

# Execução e visualização dos resultados
df = simular_fluxo()
total_bruto = df['valor bruto'].sum()
total_liquido = df['valor líquido'].sum()
perda_total = total_bruto - total_liquido

st.markdown("### Resultado da Simulação")
st.dataframe(df.style.format({"valor bruto": "R$ {:,.2f}", "valor líquido": "R$ {:,.2f}"}))

st.metric("Total Bruto", f"R$ {total_bruto:,.2f}")
st.metric("Total Líquido", f"R$ {total_liquido:,.2f}")
st.metric("Perda por Taxas", f"R$ {perda_total:,.2f}")

chart = alt.Chart(df).mark_bar().encode(
    x=alt.X('dias até recebimento:O', title='Dias até o recebimento'),
    y=alt.Y('valor líquido:Q', title='Valor líquido (R$)'),
    color='tipo:N',
    tooltip=['parcelas', 'tipo', 'valor líquido']
).properties(title='Distribuição dos recebíveis ao longo do tempo')

st.altair_chart(chart, use_container_width=True)

# Exportação para Excel
st.markdown("### Exportar Resultados")

buffer_excel = BytesIO()
with pd.ExcelWriter(buffer_excel, engine='xlsxwriter') as writer:
    df.to_excel(writer, sheet_name='Simulação', index=False)
    resumo_df = pd.DataFrame({
        "Descrição": ["Total Bruto", "Total Líquido", "Perda por Taxas"],
        "Valor (R$)": [total_bruto, total_liquido, perda_total]
    })
    resumo_df.to_excel(writer, sheet_name='Resumo', index=False)

st.download_button(
    label="📥 Baixar como Excel",
    data=buffer_excel.getvalue(),
    file_name="simulacao_fluxo_ingressos.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# Exportação para PDF
buffer_pdf = BytesIO()
pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=12)
pdf.cell(200, 10, txt="Simulação de Fluxo de Ingressos", ln=True, align='C')
pdf.ln(10)
pdf.cell(200, 10, txt=f"Total Bruto: R$ {total_bruto:,.2f}", ln=True)
pdf.cell(200, 10, txt=f"Total Líquido: R$ {total_liquido:,.2f}", ln=True)
pdf.cell(200, 10, txt=f"Perda por Taxas: R$ {perda_total:,.2f}", ln=True)
pdf.ln(10)
pdf.set_font("Arial", size=10)
pdf.cell(200, 10, txt="Resumo por parcela:", ln=True)

for index, row in df.iterrows():
    linha = f"{int(row['parcelas'])}x ({row['tipo']}) - {int(row['dias até recebimento'])} dias: R$ {row['valor líquido']:,.2f}"
    pdf.cell(200, 8, txt=linha, ln=True)

pdf.output(buffer_pdf)

st.download_button(
    label="📄 Baixar como PDF",
    data=buffer_pdf.getvalue(),
    file_name="simulacao_fluxo_ingressos.pdf",
    mime="application/pdf"
)
