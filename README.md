# Web Scraper Atacadista (Playwright + GraphQL)

Um robô de automação construído com Python e Playwright para extração de preços em e-commerces atacadistas baseados na plataforma VTEX IO.

## O Projeto

Este MVP foi desenvolvido para coletar dados estruturados de preços de atacado, superando desafios comuns de web scraping, como cache de sessão persistente, modais dinâmicos e variação de layout. Ao invés da raspagem de tela tradicional (DOM parsing), a aplicação intercepta diretamente o tráfego da API GraphQL, garantindo precisão dos dados e alta velocidade de execução.

### Funcionalidades
- Automação Resiliente: Tratamento dinâmico de banners de cookies, pop-ups de modalidade de compra e formulários de CEP, baseando-se no estado em tempo real da interface.
- Interceptação de Rede: Captura assíncrona da chamada ProductsQuery nativa da VTEX.
- Filtro de Sanitização: Higienização dos resultados para descarte de falsos positivos gerados por algoritmos de busca (produtos correlatos em caso de falta de estoque).
- Exportação de Dados: Geração automática de relatórios estruturados no formato CSV.

## Tecnologias Utilizadas
- Python 3.x
- Playwright (Sync API)
- VTEX IO (Target System)

## Como Executar

1. Clone este repositório:
   git clone https://github.com/MatheusDevCoelho/scraper-atacadista.git
   cd scraper-atacadista

2. Instale as dependências:
   pip install playwright
   playwright install chromium

3. Execute a aplicação:
   python scraper.py

4. Verificação: O payload JSON bruto será salvo no diretório debug/ e o relatório final será gerado na raiz do projeto como relatorio_nutella.csv.