import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Simulador de Fluxo de Ingressos", layout="centered")
st.title("🎟️ Simulador de Fluxo de Recebíveis de Ingressos")

# Inputs do usuário
total_vendas = st.number_input("Total bruto de vendas (R$)", min_value=0.0, value=100000.0, step=1000.0)
evento_em_dias = st.slider("Dias até o evento", min_value=30, max_value=180, value=90, step=15)
taxa_antecipacao_mensal = st.slider("Taxa de antecipação mensal (%)", min_value=0.5, max_value=5.0, value=2.0, step=0.1) / 100
rendimento_mensal_aplicacao = st.slider("Rendimento mensal da aplicação (%)", min_value=0.5, max_value=2.0, value=1.05, step=0.05) / 100

st.markdown("### Distribuição das vendas por parcelamento")
parcelamento_distribuicao = {}
for p in [1, 2, 3, 6, 12]:
    parcela_pct = st.slider(f"{p}x", 0, 100, 20 if p in [1, 2, 3] else 20, step=5)
    parcelamento_distribuicao[p] = parcela_pct / 100

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
            if dias_ate_recebimento <= evento_em_dias:
                dados.append({
                    'parcelas': parcelas,
                    'tipo': 'Fluxo',
                    'dias até recebimento': dias_ate_recebimento,
                    'valor bruto': valor_parcela,
                    'valor líquido': valor_parcela
                })
            else:
                meses_antecipacao = dias_ate_recebimento / 30
                valor_antecipado = valor_parcela * ((1 - taxa_antecipacao_mensal) ** meses_antecipacao)
                meses_aplicacao = evento_em_dias / 30
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

# Gráfico opcional
import altair as alt
chart = alt.Chart(df).mark_bar().encode(
    x=alt.X('dias até recebimento:O', title='Dias até o recebimento'),
    y=alt.Y('valor líquido:Q', title='Valor líquido (R$)'),
    color='tipo:N',
    tooltip=['parcelas', 'tipo', 'valor líquido']
).properties(title='Distribuição dos recebíveis ao longo do tempo')

st.altair_chart(chart, use_container_width=True)
