# MVP Web Scraper Atacadista

API em Python que consulta em tempo real os preços de atacado de redes de atacarejo (começando pelo Atacadão), pensada para ajudar pequenos comerciantes — pizzarias, sorveterias — a comparar preço de insumo sem precisar visitar cada loja fisicamente.

## Como funciona

Em vez de fazer scraping de HTML (frágil, quebra a cada mudança de layout), a aplicação usa Playwright para abrir uma sessão de navegador real, aplicar a localização/CEP pela interface, e então **intercepta diretamente a resposta da API GraphQL interna** que o próprio site usa internamente (plataforma VTEX IO). Isso garante dados estruturados e precisos, sem depender de seletores CSS instáveis.

A sessão do navegador fica "quente" — aberta e com localização já configurada — durante todo o tempo em que a API estiver no ar. Cada requisição HTTP reaproveita essa mesma sessão, em vez de abrir e fechar o navegador a cada busca.

### Nota técnica sobre cobertura geográfica

Durante a investigação inicial, testamos múltiplos CEPs da capital do Rio de Janeiro e do Sul Fluminense (incluindo a cidade natal do autor, Engenheiro Paulo de Frontin) e confirmamos que **o e-commerce do Atacadão atualmente não atende essas regiões para vendas online**, apesar de existirem lojas físicas da rede no interior do RJ (ex: Volta Redonda). Por isso, o CEP de testes usado no MVP é um CEP válido de São Paulo (`02170-901`), documentado aqui como decisão de arquitetura consciente, não como limitação escondida. O roadmap do projeto prevê agregar outras redes com cobertura real no Sul Fluminense.

## Arquitetura

```
.
├── main.py              # FastAPI: inicializa o navegador no startup, expõe os endpoints
├── database.py          # Persistência SQLite (histórico de buscas com timestamp)
├── lojas/
│   ├── base.py           # Interface comum (LojaBase) + filtro de higienização fuzzy
│   └── atacadao.py        # Implementação específica do Atacadão (VTEX IO / GraphQL)
└── requirements.txt
```

A classe `LojaBase` define o contrato que qualquer rede de atacarejo precisa implementar (`abrir_site`, `definir_localizacao`, `buscar_produto`, `extrair_produtos_brutos`). Isso permite adicionar novas lojas no futuro sem alterar a camada de API ou o filtro de qualidade de dados, que são genéricos.

O filtro de sanitização usa [TheFuzz](https://github.com/seatgeek/thefuzz) (fuzzy string matching) para descartar itens que a busca da loja retorna como "relacionados", mas não são de fato o produto buscado — um problema comum em motores de busca de e-commerce.

## Tecnologias

- **Python 3** — [Playwright (Async API)](https://playwright.dev/python/) para automação de navegador
- **FastAPI** + **Uvicorn** — servidor web assíncrono
- **SQLite** — persistência local do histórico de preços, sem dependência externa
- **TheFuzz** — similaridade de texto para sanitização de resultados

## Como executar

1. Clone o repositório e crie um ambiente virtual:
   ```bash
   git clone https://github.com/MatheusDevCoelho/scraper-atacadista.git
   cd scraper-atacadista
   python -m venv venv
   venv\Scripts\activate      # Windows
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

3. Suba o servidor:
   ```bash
   uvicorn main:app
   ```
   Na primeira inicialização, uma janela do navegador abre automaticamente, aceita cookies e configura a localização — isso leva alguns segundos. Quando o terminal mostrar `Sessão pronta. API no ar.`, a API está pronta para receber requisições.

4. Teste:
   ```
   GET http://127.0.0.1:8000/           # status da API
   GET http://127.0.0.1:8000/api/buscar?produto=nutella
   ```

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Status da API e loja ativa |
| `GET` | `/api/buscar?produto=<nome>&score_minimo=<0-100>` | Busca o produto na loja ativa, filtra por similaridade e retorna JSON. `score_minimo` é opcional (padrão 60). |

Cada busca bem-sucedida é persistida em `precos.db` (SQLite), com produto, preço, termo buscado, score de similaridade e data/hora — permitindo consultar histórico de preços no futuro, não só o valor mais recente.

## Roadmap

- [ ] Adicionar novas lojas de atacarejo com cobertura real no Sul Fluminense/interior do RJ
- [ ] Endpoint de histórico de preços por produto (`/api/historico?produto=X`)
- [ ] Interface web simples para o comerciante buscar sem precisar da API diretamente
- [ ] Comparação de preço entre lojas para o mesmo produto (usando o score do TheFuzz para casar itens equivalentes)