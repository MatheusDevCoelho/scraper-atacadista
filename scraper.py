"""
scraper.py — MVP Web Scraper Atacadista
Objetivo: simular a busca de um pequeno comerciante, definindo a
localização via CEP, capturando o JSON da API GraphQL (VTEX IO),
filtrando estritamente os produtos e exportando um relatório estruturado em CSV.
"""

import csv
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

CEP_TESTE = "02170-901"      # Vila Maria, São Paulo - SP
NUMERO_TESTE = "100"         # Número fictício para fluxo de endereço completo
COMPLEMENTO_TESTE = ""       
PRODUTO_TESTE = "Nutella"
PASTA_DEBUG = Path("debug")
PASTA_DEBUG.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Funções de Interação e Extração
# ---------------------------------------------------------------------------

def aceitar_cookies(page):
    try:
        botao = page.get_by_role("button", name=re.compile(r"aceit|concord", re.I))
        botao.click(timeout=5000)
        print("  -> Banner de cookies aceito.")
    except PlaywrightTimeoutError:
        print("  -> Nenhum banner de cookies encontrado.")

def definir_localizacao(page, cep: str, numero: str, complemento: str = ""):
    print(f"Definindo localização para o CEP: {cep}")
    
    try:
        page.get_by_role("button", name=re.compile(r"informar localiza", re.I)).click(timeout=4000)
    except PlaywrightTimeoutError:
        pass  

    try:
        card_atacado = page.get_by_text(re.compile(r"comprar direto do atacado", re.I))
        card_atacado.wait_for(state="visible", timeout=3000)
        card_atacado.click(timeout=3000)
        print("  -> Modalidade 'Comprar direto do Atacado' selecionada.")
        page.wait_for_timeout(1000)
    except PlaywrightTimeoutError:
        pass

    try:
        input_cep = page.get_by_placeholder(re.compile(r"00000-000|cep", re.I))
        input_cep.wait_for(state="visible", timeout=4000)
        
        if cep not in input_cep.input_value():
            input_cep.fill(cep)
            input_cep.press("Tab")
            page.wait_for_timeout(2000)
            print("  -> CEP preenchido com sucesso.")
        else:
            print("  -> CEP já preenchido pelo cache da sessão.")
    except PlaywrightTimeoutError:
        pass

    confirmado = False
    try:
        botao_confirmar_loja = page.get_by_role("button", name=re.compile(r"^confirmar$", re.I))
        if botao_confirmar_loja.is_visible(timeout=3000):
            botao_confirmar_loja.click(timeout=3000)
            confirmado = True
            print("  -> Loja próxima confirmada via cache.")
    except Exception:
        pass

    if not confirmado:
        input_numero = None
        for seletor in (
            page.get_by_placeholder(re.compile(r"n[uú]mero|^n[ºo°]", re.I)),
            page.get_by_label(re.compile(r"n[uú]mero", re.I)),
        ):
            try:
                seletor.wait_for(state="visible", timeout=2000)
                input_numero = seletor
                break
            except PlaywrightTimeoutError:
                continue

        if input_numero:
            input_numero.fill(numero)
            try:
                page.get_by_role("button", name=re.compile(r"confirmar|continuar|salvar|avançar", re.I)).click(timeout=3000)
                print("  -> Endereço completo confirmado.")
            except Exception:
                pass
        else:
            try:
                page.get_by_role("button", name=re.compile(r"confirmar|continuar|salvar|avançar", re.I)).click(timeout=3000)
                print("  -> Confirmação genérica acionada.")
            except Exception:
                pass

    page.wait_for_timeout(2000)
    print("  -> Localização aplicada!")

def buscar_produto(page, termo: str) -> dict:
    print(f"Buscando produto: {termo}")
    campo_busca = page.get_by_placeholder(re.compile(r"busca|pesquis", re.I))
    campo_busca.click()
    campo_busca.fill(termo)

    with page.expect_response(
        lambda r: "operationName=ProductsQuery" in r.url and r.status == 200,
        timeout=15000,
    ) as info_resposta:
        campo_busca.press("Enter")

    dados = info_resposta.value.json()
    caminho_saida = PASTA_DEBUG / f"resultado_{termo.lower()}.json"
    caminho_saida.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  -> JSON capturado e salvo em {caminho_saida}")
    return dados

def exportar_csv(produtos_filtrados, termo):
    caminho_csv = Path(f"relatorio_{termo.lower()}.csv")
    with open(caminho_csv, mode="w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.writer(arquivo, delimiter=";")
        escritor.writerow(["Produto", "Preço Atacado (R$)"])
        for p in produtos_filtrados:
            escritor.writerow([p["nome"], p["preco"]])
    print(f"\n✅ Relatório exportado com sucesso para: {caminho_csv}")

# ---------------------------------------------------------------------------
# Orquestração Principal
# ---------------------------------------------------------------------------

def testar_acesso():
    with sync_playwright() as p:
        print("\n🚀 Iniciando o robô...")
        browser = p.chromium.launch(headless=False, slow_mo=150)
        page = browser.new_page()

        try:
            page.goto("https://www.atacadao.com.br", wait_until="domcontentloaded")
            aceitar_cookies(page)
            definir_localizacao(page, CEP_TESTE, NUMERO_TESTE, COMPLEMENTO_TESTE)
            dados = buscar_produto(page, PRODUTO_TESTE)

            try:
                produtos = dados.get("data", {}).get("search", {}).get("products", {}).get("edges", [])
                
                print(f"\nResultados filtrados para '{PRODUTO_TESTE}':")
                print("-" * 50)
                
                lista_para_exportar = []
                for item in produtos:
                    node = item.get("node", {})
                    nome = str(node.get("name", "Nome indisponível")).strip()
                    preco = node.get("offers", {}).get("lowPrice", 0.00)
                    
                    # Filtro estrito: O comerciante só quer Nutella de verdade
                    if "nutella" in nome.lower():
                        print(f"  📦 {nome} | R$ {preco}")
                        lista_para_exportar.append({"nome": nome, "preco": preco})
                
                print("-" * 50)
                print(f"Total de itens exportáveis encontrados: {len(lista_para_exportar)}")
                
                if lista_para_exportar:
                    exportar_csv(lista_para_exportar, PRODUTO_TESTE)
                else:
                    print(f"⚠️ Produto '{PRODUTO_TESTE}' em falta ou não atendeu ao filtro de qualidade.")
                    
            except (KeyError, TypeError) as e:
                print(f"\n❌ Erro ao mapear o JSON: {e}")

        except Exception as e:
            page.screenshot(path=str(PASTA_DEBUG / "erro_geral.png"))
            print(f"\n❌ Ocorreu um erro no acesso: {e}")
            print("Screenshot salvo em debug/erro_geral.png para investigarmos.")

        finally:
            print("Fechando o navegador...\n")
            browser.close()

if __name__ == "__main__":
    testar_acesso()