# Diário de Bordo — MVP Web Scraper Atacadista

## [Sprint 01] — Mapeamento de Escopo e Viabilidade Logística
- **Objetivo:** Definir a viabilidade técnica e a arquitetura para automação de consulta de preços atacadistas.
- **Descobertas:** 
  - **Assaí Atacadista:** A plataforma web exibe os encartes promocionais apenas em formato de imagem (PNG/JPG). A extração estruturada de dados exigiria um motor pesado de OCR, inviabilizando um MVP leve e rápido.
  - **Atacadão:** Utiliza a plataforma VTEX IO. Durante os testes, identificou-se uma restrição de malha logística digital, impossibilitando a exibição de preços e estoques para CEPs de determinadas regiões do interior do RJ.
- **Decisão Arquitetural:** Construir a POC (Proof of Concept) focada no Atacadão, utilizando um CEP Mock de São Paulo (`02170-901`) para validar o motor de extração, documentando a barreira logística como uma regra de negócio do e-commerce.

## [Sprint 02] — Engenharia Reversa, Resiliência de Interface e Sanitização
- **Desenvolvimento:**
  - **Setup:** Inicialização do projeto com Python e Playwright.
  - **Interceptação de API:** Implementação de captura de rede assíncrona (`page.expect_response`) focada no payload JSON do GraphQL da VTEX (`ProductsQuery`). Isso eliminou a necessidade de fazer parsing complexo e frágil no DOM HTML.
  - **Tratamento de Estado:** Desenvolvimento de blocos condicionais inteligentes para lidar com o cache de sessão e o comportamento volátil da UI (ex: o pop-up "Como deseja comprar?" e o auto-preenchimento do CEP).
  - **Qualidade de Dados:** Criação de um filtro de sanitização estrito. O motor de busca da plataforma muitas vezes retorna itens substitutos ou com tags semelhantes (ex: produtos de limpeza com aroma de avelã quando busca-se Nutella). O filtro implementado garante que apenas os itens genuínos sejam mapeados.
- **Entrega:** Robô resiliente concluído. O script navega, aplica a localização, intercepta o tráfego de rede, higieniza os dados e exporta um arquivo `.csv` estruturado pronto para análise.