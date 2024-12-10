import streamlit as st
import joblib
import pandas as pd
import plotly.graph_objects as go
from plotly.graph_objs import Sankey
from collections import Counter
from wordcloud import WordCloud
import time

# Autenticação do GSheets
import os
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Configurando autenticação do Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = None

# URL do arquivo token.json no GitHub
GITHUB_CREDENTIALS_URL = "https://github.com/dreymond1/streamlitapp/blob/main/token.json"

# Faz o download do arquivo token.json do GitHub
def download_credentials_from_github(url, filename="token.json"):
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, "wb") as file:
            file.write(response.content)
    else:
        raise Exception(f"Erro ao baixar o arquivo: {response.status_code}")

# Baixar o credentials.json se não existir
if not os.path.exists('token.json'):
    download_credentials_from_github(GITHUB_CREDENTIALS_URL)

# Processo de autenticação
if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

# Configurando o serviço do Google Sheets
service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()

# Carregar o modelo Naive Bayes
model = joblib.load('modelo_naive_bayes.pkl')

# Carregar o vetorizador
vectorizer = joblib.load('vectorizer.pkl')

#  Título da página
st.set_page_config(page_title="Análise de Sentimento", page_icon="🔍", layout="centered")

# Barra lateral que analisa sentimentos de uma planilha sheets
with st.sidebar:
    
    st.header("Analisar sentimentos de uma planilha Sheets 📗")
    st.info("Os campos deverão ser preenchidos de forma correta. Caso contrário, a previsão não será bem sucedida.")
    # Inputs
    st.markdown("### Instruções estão dentro de cada campo")
    
    id_input = st.text_input("ID:", placeholder="Exemplo: 1YYvqp_w9zDIgjNHFC8mh7Rkku6gKRN7Rwo8ydHKCqVA")
    
    aba_input = st.text_input("Nome da Aba:", placeholder="Exemplo: Aba-teste")
    
    coluna_comentario_input = st.text_input("Nome da Coluna de Comentário:", placeholder="Exemplo: A")
    
    coluna_sentimento_input = st.text_input("Nome da Coluna de Sentimento:", placeholder="Exemplo: B")

    if id_input == "" or aba_input == "" or coluna_comentario_input == "" or coluna_sentimento_input == "":
        st.error("Preencha todos os campos antes de analisar!")
    else:
        if st.button("Analisar Sentimentos da Planilha Sheets"):
            # ID da planilha e nome da aba
            SPREADSHEET_ID = id_input
            SHEET_NAME = aba_input
            COMMENT_COLUMN = coluna_comentario_input
            SENTIMENT_COLUMN = coluna_sentimento_input
            
            # Função para prever sentimento
            def analyze_sentiment(comment):
                sentimento_vec = vectorizer.transform([comment])  # Passar como lista
                sentimento_pred = model.predict(sentimento_vec)
                return str(sentimento_pred[0]) 
            
            # Função que recebe os valores da planilha e modificada
            def process_comments_and_sentiments():
            
                # Obtendo os dados da planilha
                range_to_read = f"{SHEET_NAME}!{COMMENT_COLUMN}:{SENTIMENT_COLUMN}"
                result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=range_to_read).execute()
                rows = result.get('values', [])
            
                # Preparar os dados para escrita (incluindo cabeçalhos)
                updates = []
                for i, row in enumerate(rows):
                    if i == 0:
                        continue  # Ignorar cabeçalhos, se houver
                    comment = row[0] if len(row) > 0 else ""  # Verificar se há comentário
                    sentiment = row[1] if len(row) > 1 else ""  # Verificar se há sentimento
            
                    if comment and not sentiment:  # Só processa se houver comentário sem sentimento
                        predicted_sentiment = analyze_sentiment(comment)
                        updates.append({'range': f"{SHEET_NAME}!{SENTIMENT_COLUMN}{i+1}",
                                        'values': [[predicted_sentiment]]})
            
                # Atualizar a planilha com os sentimentos
                if updates:
                    body = {'valueInputOption': 'RAW', 'data': updates}
                    service.spreadsheets().values().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
            
                print(f"Processamento concluído!")
            
            # Executar
            process_comments_and_sentiments()

# Título e descrição do aplicativo
st.markdown("## 🔍 Análise de Sentimento de Comentários")
st.write(
    """
    Este aplicativo utiliza Machine Learning para prever o sentimento de um comentário.
    Basta inserir o texto e clicar em **Analisar Sentimento** para ver o resultado.
    """
)

# Contador de análises
if "contador_analises" not in st.session_state:
    st.session_state.contador_analises = 0

st.markdown(f"**📊 Total de Análises Realizadas:** {st.session_state.contador_analises}")

# Inicializar contadores de acertos e total de previsões
if "total_previsoes" not in st.session_state:
    st.session_state.total_previsoes = 0
if "acertos" not in st.session_state:
    st.session_state.acertos = 0

# Entrada de Texto
st.markdown("### ✍️ Digite o comentário para análise:")
text_input = st.text_area(
    "Insira o comentário aqui:", 
    placeholder="Exemplo: O produto é incrível e superou minhas expectativas!"
)

# Botão de Previsão
if st.button("Analisar Sentimento"):
    st.session_state.contador_analises += 1

    if text_input.strip():
        # Transformar o texto e prever o sentimento
        sentimento_vec = vectorizer.transform([text_input])  # Passar como lista
        sentimento_pred = model.predict(sentimento_vec)

        # Exibir resultado com formatação
        st.markdown("#### 🎯 Resultado da Análise:")
        if sentimento_pred[0] == "Positivo": 
            st.success(f"Sentimento Previsto: **Positivo** 😊")
        elif sentimento_pred[0] == "Negativo":
            st.error(f"Sentimento Previsto: **Negativo** 😠")
        else:
            st.info(f"Sentimento Previsto: **Neutro** 😐")

        # Solicitar feedback do usuário
        feedback = st.radio(
            "Selecione o sentimento correto (se o modelo errou):",
            options=["Modelo está correto", "Modelo está errado"],
            index=None
        )
          # Atualizar contadores de acertos
        if feedback == "Modelo está correto":
            st.session_state.acertos += 1
            st.session_state.total_previsoes += 1
        else:
            st.session_state.total_previsoes += 1

        # Calcular e exibir a acurácia
        acuracia = (st.session_state.acertos / st.session_state.total_previsoes) * 100
        st.markdown(
            f"**📊 Acurácia Atual (baseada em {st.session_state.total_previsoes} previsões):** "
            f"<span style='color:green;font-size:20px'><b>{acuracia:.2f}%</b></span>",
            unsafe_allow_html=True
        )
    else:
        st.warning("⚠️ Por favor, insira um comentário para analisar o sentimento.")
        
#st.session_state.acertos = 0
#st.session_state.total_previsoes = 0
#st.session_state.contador_analises = 0


st.markdown("---")

# Upload de CSV para análise em massa
st.markdown("### 📂 Faça upload de um arquivo CSV com comentários:")
uploaded_file = st.file_uploader("Escolha um arquivo CSV (deve possuir pelo menos uma coluna chamada 'Comentário')", type=["csv"])

if uploaded_file:
    data = pd.read_csv(uploaded_file, encoding='iso-8859-1', sep=';', on_bad_lines='skip')

    st.write("📊 **Dados carregados com sucesso!**")

    st.dataframe(data.head())

    # Botão para iniciar a análise em massa
    if st.button("Analisar Sentimentos no CSV"):
        with st.spinner("Carregando..."):
            progress_bar = st.progress(0)
            for i in range(101):
                time.sleep(0.05)
                progress_bar.progress(i)

        # Vetorizar os comentários
        comentarios_vec = vectorizer.transform(data['Comentário'])

        # Prever sentimentos
        data['Sentimento'] = model.predict(comentarios_vec)

        # Exibir resultado
        st.markdown("#### 📋 Resultado da Análise:")
        st.dataframe(data[['Comentário', 'Sentimento']])

        # Gráficos de distribuição dos sentimentos usando plotly
        st.markdown("#### 📊 Visualização dos Sentimentos:")

        # Contagem de cada sentimento
        sentiment_count = data['Sentimento'].value_counts(normalize=True).reset_index()
        sentiment_count.columns = ['Sentimento', 'Proporcao']

        sentiment_count['Proporcao'] = sentiment_count['Proporcao'] * 100

        # Adicionar as porcentagens para cada sentimento
        sentiment_count['Proporcao_Label'] = sentiment_count['Proporcao'].round(2).astype(str) + '%'

        # Contagem de cada sentimento
        sentiment_count_2 = data['Sentimento'].value_counts()
        
        # Exibir contagens
        st.markdown("##### Sentimentos identificados:")
        st.write(f"**Positivo:** {sentiment_count_2.get('Positivo', 0)}")
        st.write(f"**Negativo:** {sentiment_count_2.get('Negativo', 0)}")
        st.write(f"**Neutro:** {sentiment_count_2.get('Neutro', 0)}")

        # Criar gráfico de barras 100%
        fig_stack = go.Figure()

         # Barra para o Sentimento Negativo
        fig_stack.add_trace(go.Bar(
            x=['Sentimentos'],
            y=sentiment_count.loc[sentiment_count['Sentimento'] == 'Negativo', 'Proporcao'],
            name='Negativo',
            marker=dict(color='red'),
            text=sentiment_count.loc[sentiment_count['Sentimento'] == 'Negativo', 'Proporcao_Label'],
            hoverinfo='text',
        ))

        # Barra para o sentimento positivo
        fig_stack.add_trace(go.Bar(
            x=['Sentimentos'],
            y=sentiment_count.loc[sentiment_count['Sentimento'] == 'Positivo', 'Proporcao'],
            name='Positivo',
            marker=dict(color='green'),
            text=sentiment_count.loc[sentiment_count['Sentimento'] == 'Positivo', 'Proporcao_Label'],
            hoverinfo='text',
        ))

        # Barra para o sentimento seutro
        fig_stack.add_trace(go.Bar(
            x=['Sentimentos'],
            y=sentiment_count.loc[sentiment_count['Sentimento'] == 'Neutro', 'Proporcao'],
            name='Neutro',
            marker=dict(color='yellow'),
            text=sentiment_count.loc[sentiment_count['Sentimento'] == 'Neutro', 'Proporcao_Label'],
            hoverinfo='text',
        ))


        # Ajustar o layout
        fig_stack.update_layout(
            barmode='stack',
            title="Distribuição dos Sentimentos (%) - Empilhado",
            xaxis=dict(title='Sentimentos'),
            yaxis=dict(title='Porcentagem (%)', range=[0, 100]),
            showlegend=True
        )

        st.plotly_chart(fig_stack)

        # Criar gráfico de barras lado a lado
        fig_side_by_side = go.Figure()

        # Barra para o sentimento positivo
        fig_side_by_side.add_trace(go.Bar(
            x=['Sentimentos'],
            y=sentiment_count.loc[sentiment_count['Sentimento'] == 'Positivo', 'Proporcao'],
            name='Positivo',
            marker=dict(color='green'),
            text=sentiment_count.loc[sentiment_count['Sentimento'] == 'Positivo', 'Proporcao_Label'],
            hoverinfo='text',
        ))    

         # Barra para o sentimento neutro
        fig_side_by_side.add_trace(go.Bar(
            x=['Sentimentos'],
            y=sentiment_count.loc[sentiment_count['Sentimento'] == 'Neutro', 'Proporcao'],
            name='Neutro',
            marker=dict(color='yellow'),
            text=sentiment_count.loc[sentiment_count['Sentimento'] == 'Neutro', 'Proporcao_Label'],
            hoverinfo='text',
        ))


        # Barra para o sentimento negativo
        fig_side_by_side.add_trace(go.Bar(
            x=['Sentimentos'],
            y=sentiment_count.loc[sentiment_count['Sentimento'] == 'Negativo', 'Proporcao'],
            name='Negativo',
            marker=dict(color='red'),
            text=sentiment_count.loc[sentiment_count['Sentimento'] == 'Negativo', 'Proporcao_Label'],
            hoverinfo='text',
        ))

        # Ajustar o layout
        fig_side_by_side.update_layout(
            barmode='group',
            title="Distribuição dos Sentimentos (%) - Lado a Lado",
            xaxis=dict(title='Sentimentos'),
            yaxis=dict(title='Porcentagem (%)', range=[0, 100]),
            showlegend=True
        )

        st.plotly_chart(fig_side_by_side)

        not_words = [
            'a', 'à', 'logo', 'desde', 'podem', 'além', 'q', 'sim', 'nao', 'falando', 'lá', 'meus', 'ficou', 'queren', 'sei', 'hoje', 'aqui', 'ficar', 'te', 'mas', 'neste', 'nesta', 'nessa', 'nesse', 'e', 'vou', 'vejo', 'entrará', 'estava', 'meu', 've', 'vê', 'ter', 'logo', 'fosse', 'horas', 'ainda', 'dia', 'falar', 'minuto', 'minutos', 'hora', 'pela', 'dar', 'então', 'sou', 'vou', 'ficaram', 'agora', 'os', 'me', 'algmas', 'algumas', 'alguns', 'ali', 'ambos', 'antes', 'ao', 'aos', 'apenas', 'apoio', 'apos', 'após', 'aquela', 'aquelas', 'aquele', 'aqueles', 'aquilo', 'as', 'às', 'ate', 'até', 'atras', 'atrás', 'bem', 'bom', 'cada', 'certa', 'certas', 'certeza', 'certo', 'certos', 'com', 'como', 'conforme', 'contra', 'contudo', 'da', 'da', 'dá', 'dado', 'das', 'de', 'dela', 'delas', 'dele', 'deles', 'dessa', 'dessas', 'desse', 'desses', 'desta', 'destas', 'deste', 'destes', 'deve', 'devem', 'devera', 'deverá', 'deverao', 'deverão', 'deveria', 'deveriam', 'disse', 'diz', 'dizem', 'dizer', 'do', 'dos', 'duas', 'duplo', 'duplos', 'ela', 'elas', 'ele', 'eles', 'em', 'em', 'enquanto', 'essa', 'essas', 'esse', 'esses', 'esta', 'estamos', 'estão', 'este', 'estes', 'essa', 'esses', 'e', 'eu', 'ela', 'elas', 'isto', 'isso', 'isso', 'isto', 'ja', 'já', 'jamais', 'jamas', 'lugar', 'mais', 'mas', 'mesmo', 'mesmos', 'muito', 'muitos', 'na', 'nas', 'no', 'nos', 'não', 'nós', 'nem', 'nosso', 'nossos', 'ou', 'outra', 'outras', 'outro', 'outros', 'para', 'para', 'para', 'pelo', 'pelas', 'pelo', 'perante', 'pois', 'por', 'porque', 'portanto', 'posso', 'pouca', 'poucas', 'pouco', 'poucos', 'primeiro', 'propria', 'própria', 'próprias', 'próprio', 'próprios', 'quais', 'qual', 'qualquer', 'quando', 'quanto', 'quantos', 'que', 'quem', 'quer', 'quero', 'se', 'seja', 'sejam', 'sejamos', 'sem', 'sempre', 'sendo', 'ser', 'sera', 'será', 'serao', 'serão', 'seria', 'seriam', 'seu', 'seus', 'si', 'sido', 'so', 'só', 'sob', 'sobre', 'sua', 'suas', 'talvez', 'tambem', 'também', 'tanta', 'tantas', 'tanto', 'tao', 'tão', 'te', 'tem', 'temos', 'tendo', 'tenha', 'tenham', 'tenhamos', 'tenho', 'tens', 'ter', 'tera', 'terá', 'terao', 'terão', 'teria', 'teriam', 'teu', 'teus', 'teve', 'tinha', 'tinham', 'tive', 'tivemos', 'tiver', 'tivera', 'tiveram', 'tiverem', 'tivermos', 'tivesse', 'tivessem', 'tivessemos', 'tivéssemos', 'toda', 'todas', 'todo', 'todos', 'tu', 'tua', 'tuas', 'tudo', 'ultimo', 'último', 'um', 'uma', 'umas', 'uns', 'vai', 'vao', 'vão', 'vem', 'vêm', 'vendo', 'ver', 'vez', 'vindo', 'vir', 'voce', 'você', 'voces', 'vocês', 'vos'
            'a', 'o', 'é', 'mim', 'pra', 'há', 'foi', 'à', 'ainda', 'agora', 'fui', 'estou', 'depois', 'meu', 'p', '','algmas', 'algumas', 'alguns', 'ali', 'ambos', 'antes', 'ao', 'aos', 'apenas', 'apoio', 'apos', 'após', 'aquela', 'aquelas', 'aquele', 'aqueles', 'aquilo', 'as', 'às', 'ate', 'até', 'atras', 'atrás', 'bem', 'bom', 'cada', 'certa', 'certas', 'certeza', 'certo', 'certos', 'com', 'como', 'conforme', 'contra', 'contudo', 'da', 'da', 'dá', 'dado', 'das', 'de', 'dela', 'delas', 'dele', 'deles', 'dessa', 'dessas', 'desse', 'desses', 'desta', 'destas', 'deste', 'destes', 'deve', 'devem', 'devera', 'deverá', 'deverao', 'deverão', 'deveria', 'deveriam', 'disse', 'diz', 'dizem', 'dizer', 'do', 'dos', 'duas', 'duplo', 'duplos', 'ela', 'elas', 'ele', 'eles', 'em', 'em', 'enquanto', 'essa', 'essas', 'esse', 'esses', 'esta', 'estamos', 'estão', 'este', 'estes', 'essa', 'esses', 'e', 'eu', 'ela', 'elas', 'isto', 'isso', 'isso', 'isto', 'ja', 'já', 'jamais', 'jamas', 'lugar', 'mais', 'mas', 'mesmo', 'mesmos', 'muito', 'muitos', 'na', 'nas', 'no', 'nos', 'não', 'nós', 'nem', 'nosso', 'nossos', 'ou', 'outra', 'outras', 'outro', 'outros', 'para', 'para', 'para', 'pelo', 'pelas', 'pelo', 'perante', 'pois', 'por', 'porque', 'portanto', 'posso', 'pouca', 'poucas', 'pouco', 'poucos', 'primeiro', 'propria', 'própria', 'próprias', 'próprio', 'próprios', 'quais', 'qual', 'qualquer', 'quando', 'quanto', 'quantos', 'que', 'quem', 'quer', 'quero', 'se', 'seja', 'sejam', 'sejamos', 'sem', 'sempre', 'sendo', 'ser', 'sera', 'será', 'serao', 'serão', 'seria', 'seriam', 'seu', 'seus', 'si', 'sido', 'so', 'só', 'sob', 'sobre', 'sua', 'suas', 'talvez', 'tambem', 'também', 'tanta', 'tantas', 'tanto', 'tao', 'tão', 'te', 'tem', 'temos', 'tendo', 'tenha', 'tenham', 'tenhamos', 'tenho', 'tens', 'ter', 'tera', 'terá', 'terao', 'terão', 'teria', 'teriam', 'teu', 'teus', 'teve', 'tinha', 'tinham', 'tive', 'tivemos', 'tiver', 'tivera', 'tiveram', 'tiverem', 'tivermos', 'tivesse', 'tivessem', 'tivessemos', 'tivéssemos', 'toda', 'todas', 'todo', 'todos', 'tu', 'tua', 'tuas', 'tudo', 'ultimo', 'último', 'um', 'uma', 'umas', 'uns', 'vai', 'vao', 'vão', 'vem', 'vêm', 'vendo', 'ver', 'vez', 'vindo', 'vir', 'voce', 'você', 'voces', 'vocês', 'vos'
        ]

         # Criar diagrama de Sankey
        st.markdown("#### 🧠 Diagrama de Sankey:")
        
        palavras_positivas = data[data['Sentimento'] == 'Positivo']['Comentário'].dropna().astype(str).str.lower()
        palavras_negativas = data[data['Sentimento'] == 'Negativo']['Comentário'].dropna().astype(str).str.lower()
        palavras_neutras = data[data['Sentimento'] == 'Neutro']['Comentário'].dropna().astype(str).str.lower()
        
        # Remover palavras irrelevantes
        palavras_positivas = ' '.join(palavras_positivas.apply(lambda x: ' '.join([word for word in x.split() if word not in not_words])))
        palavras_negativas = ' '.join(palavras_negativas.apply(lambda x: ' '.join([word for word in x.split() if word not in not_words])))
        palavras_neutras = ' '.join(palavras_neutras.apply(lambda x: ' '.join([word for word in x.split() if word not in not_words])))

        prop_pos = int((sentiment_count_2.get('Positivo', 0)/sentiment_count_2.sum()).round(1)*10)+2
        prop_neg = int((sentiment_count_2.get('Negativo', 0)/sentiment_count_2.sum()).round(1)*10)+2
        prop_neu = int((sentiment_count_2.get('Neutro', 0)/sentiment_count_2.sum()).round(1)*10)+2
        
        # Pegando as palavras de forma proporcional
        freq_positivas = Counter(palavras_positivas.split()).most_common(prop_pos)
        freq_negativas = Counter(palavras_negativas.split()).most_common(prop_neg)
        freq_neutras = Counter(palavras_neutras.split()).most_common(prop_neu)

        sentiment_count_2.get('Neutro', 0)
        
        # Criando as ligações para o gráfico de Sankey
        sentimentos = ['Positivo', 'Negativo', 'Neutro']
        
        ligacoes = []
        
        for sentimento, palavras_frequentes in zip(sentimentos, [freq_positivas, freq_negativas, freq_neutras]):
            for palavra, _ in palavras_frequentes:
                ligacoes.append((sentimento, palavra))
        
        palavras = [ligacao[1] for ligacao in ligacoes]
        sentimentos = [ligacao[0] for ligacao in ligacoes]
        
        # Criar o gráfico de Sankey
        # Gerar os rótulos para os sentimentos e palavras
        labels = list(set(palavras + sentimentos))
        label_to_index = {label: idx for idx, label in enumerate(labels)}
        
        # Construir as fontes e destinos
        origem = [label_to_index[sentimento] for sentimento in sentimentos]
        destino = [label_to_index[palavra] for palavra in palavras]
        
        # Valores das ligações (contagem de ocorrências)
        valores = [1] * len(origem)

        # Definindo a cor de cada sentimento
        link_colors = ['#a9f0a1' if sentimento == 'Positivo' else '#f57171' if sentimento == 'Negativo' else '#f7f55c' 
               for sentimento in sentimentos]

        node_border = ['#a9f0a1' if sentimento == 'Positivo' else '#f57171' if sentimento == 'Negativo' else '#f7f55c' 
               for sentimento in sentimentos]
        
        # Criar gráfico de Sankey
        fig_sankey = go.Figure(go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color=node_border, width=0.5),
                color="gray",
                label=labels
            ),
            link=dict(
                source=origem,
                target=destino,
                value=valores,
                color=link_colors
            )
        ))
        
        fig_sankey.update_layout(font_size=10)
        st.plotly_chart(fig_sankey)

        # Gerar uma WordCloud para cada sentimento
        st.markdown("#### ☁️ Nuvens de Palavras por Sentimento:")

        # Filtrar comentários por sentimento
        comments_positive = data[data['Sentimento'] == 'Positivo']['Comentário'].dropna().astype(str).str.lower()
        comments_negative = data[data['Sentimento'] == 'Negativo']['Comentário'].dropna().astype(str).str.lower()
        comments_neutral = data[data['Sentimento'] == 'Neutro']['Comentário'].dropna().astype(str).str.lower()

        # Gerar uma única string para cada sentimento
        positive_words = ' '.join(comments_positive)
        negative_words = ' '.join(comments_negative)
        neutral_words = ' '.join(comments_neutral)

        # Remover palavras irrelevantes
        positive_filtered = ' '.join(word for word in positive_words.split() if word not in not_words)
        negative_filtered = ' '.join(word for word in negative_words.split() if word not in not_words)
        neutral_filtered = ' '.join(word for word in neutral_words.split() if word not in not_words)

        # Criar as nuvens de palavras para cada sentimento
        positive_wordcloud = WordCloud(width=800, height=400, background_color='white').generate(positive_filtered)
        negative_wordcloud = WordCloud(width=800, height=400, background_color='white').generate(negative_filtered)
        neutral_wordcloud = WordCloud(width=800, height=400, background_color='white').generate(neutral_filtered)

        # Exibir as nuvens de palavras para cada sentimento usando plotly
        st.markdown("**🟩 Positivo:**")
        st.plotly_chart(go.Figure(go.Image(z=positive_wordcloud.to_array())))

        st.markdown("**🟥 Negativo:**")
        st.plotly_chart(go.Figure(go.Image(z=negative_wordcloud.to_array())))

        st.markdown("**🟨 Neutro:**")
        st.plotly_chart(go.Figure(go.Image(z=neutral_wordcloud.to_array())))

        st.success("Tudo pronto!")
        
        # Download dos resultados em CSV
        st.markdown("#### 📥 Baixe os resultados:")
        csv_result = data.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV com Sentimentos",
            data=csv_result,
            file_name="resultado_sentimentos.csv",
            mime="text/csv"
        )

# Rodapé
st.markdown("---")
st.markdown("**Criado por [Andrey Alves](https://github.com/dreymond1)** 🚀")
