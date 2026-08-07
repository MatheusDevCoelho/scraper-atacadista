import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from playwright.async_api import async_playwright

import database
from lojas.atacadao import Atacadao
from lojas.base import higienizar_produtos

CEP_PADRAO = "02170-901"      # fixture validado: e-commerce do Atacadão só atende SP
NUMERO_PADRAO = "100"
SCORE_MINIMO_PADRAO = 60

# Serializa o acesso à aba compartilhada: só uma busca por vez usa o
# navegador "quente", evitando concorrência sobre o mesmo Page.
lock_navegador = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando Playwright e aquecendo a sessão do Atacadão...")
    database.init_db()

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False, slow_mo=100)
    page = await browser.new_page()

    loja = Atacadao(page)
    await loja.abrir_site()
    await loja.definir_localizacao(CEP_PADRAO, NUMERO_PADRAO)

    # Diagnóstico: 'Sessão pronta' não garante que a localização foi
    # realmente aplicada (os try/except internos podem ter falhado em
    # silêncio). Checamos o cookie de verdade antes de seguir.
    cookies = await page.context.cookies()
    cookie_regional = next((c for c in cookies if c["name"] == "regionalization"), None)
    if cookie_regional:
        print(f"[DIAGNÓSTICO] Cookie 'regionalization' OK: {cookie_regional['value']}")
    else:
        print("[DIAGNÓSTICO] ⚠️ Cookie 'regionalization' NÃO foi encontrado — "
              "a localização provavelmente não foi aplicada.")

    app.state.playwright = playwright
    app.state.browser = browser
    app.state.loja = loja
    print("Sessão pronta. API no ar.")

    yield

    print("Encerrando navegador...")
    await app.state.browser.close()
    await app.state.playwright.stop()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def status():
    return {
        "status": "online",
        "loja_ativa": "atacadao",
        "endpoint_busca": "/api/buscar?produto=<nome>",
    }


@app.get("/api/buscar")
async def buscar(produto: str, score_minimo: int = SCORE_MINIMO_PADRAO):
    if not produto or not produto.strip():
        raise HTTPException(status_code=400, detail="Parâmetro 'produto' é obrigatório.")

    async with lock_navegador:
        loja = app.state.loja
        try:
            dados_brutos = await loja.buscar_produto(produto)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Falha ao consultar a loja: {e}")

    produtos_extraidos = loja.extrair_produtos_brutos(dados_brutos)
    produtos_limpos = higienizar_produtos(produtos_extraidos, produto, score_minimo)

    database.salvar_resultados("atacadao", produto, produtos_limpos)

    return {
        "termo_buscado": produto,
        "loja": "atacadao",
        "total_encontrado": len(produtos_limpos),
        "produtos": produtos_limpos,
    }