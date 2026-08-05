"""
scraper.py — MVP Web Scraper Atacadista
Objetivo: arquitetura orientada a objetos para busca dinâmica em e-commerces atacadistas,
interceptando a API GraphQL (VTEX IO) e aplicando Fuzzy Matching para higienização de dados.
"""

import csv
import json
import re
import traceback
from datetime import datetime
from pathlib import Path
from thefuzz import fuzz

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ---------------------------------------------------------------------------
# Configuração Global
# ---------------------------------------------------------------------------

CEP_TESTE = "02170-901"      # Vila Maria, São Paulo - SP (Mock para contornar malha logística)
NUMERO_TESTE = "100"         
PASTA_DEBUG = Path("debug")

# ---------------------------------------------------------------------------
# Arquitetura Orientada a Objetos (Base e Implementação)
# ---------------------------------------------------------------------------

class LojaBase:
    """
    Classe abstrata que define o contrato para qualquer e-commerce atacadista
    e fornece métodos de depuração padrão.
    """
    def __init__(self, page):
        self.page = page
        self.pasta_debug = PASTA_DEBUG
        self.pasta_debug.mkdir(exist_ok=True)

    def salvar_evidencia_erro(self, contexto: str):
        """Gera um dump da tela (Screenshot + HTML) em caso de falha."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefixo = f"{contexto}_{timestamp}"
        
        caminho_img = self.pasta_debug / f"{prefixo}.png"
        caminho_html = self.pasta_debug / f"{prefixo}.html"
        
        print(f"\n[DEBUG] ⚠️ Falha detectada no bloco: '{contexto}'")
        print("[DEBUG] 📸 Gerando evidências...")
        
        try:
            self.page.screenshot(path=str(caminho_img))
            caminho_html.write_text(self.page.content(), encoding="utf-8")
            print(f"  -> Print salvo em: {caminho_img}")
            print(f"  -> HTML salvo em: {caminho_html}\n")
        except Exception as e:
            print(f"  -> Falha ao tentar salvar evidências: {e}\n")

    def abrir_site(self):
        raise NotImplementedError

    def definir_localizacao(self, cep: str, numero: str):
        raise NotImplementedError

    def buscar_produto(self, termo: str) -> dict:
        raise NotImplementedError


class Atacadao(LojaBase):
    """
    Implementação específica para a plataforma VTEX IO do Atacadão.
    """
    def abrir_site(self):
        try:
            self.page.goto("https://www.atacadao.com.br", wait_until="domcontentloaded")
            self._aceitar_cookies()
        except Exception as e:
            self.salvar_evidencia_erro("abrir_site_atacadao")
            raise e

    def _aceitar_cookies(self):
        try:
            botao = self.page.get_by_role("button", name=re.compile(r"aceit|concord", re.I))
            botao.click(timeout=5000)
            print("  -> Banner de cookies aceito.")
        except PlaywrightTimeoutError:
            print("  -> Nenhum banner de cookies encontrado.")

    def definir_localizacao(self, cep: str, numero: str):
        print(f"Definindo localização para o CEP: {cep}")
        try:
            try:
                self.page.get_by_role("button", name=re.compile(r"informar localiza", re.I)).click(timeout=4000)
            except PlaywrightTimeoutError:
                pass  

            try:
                card_atacado = self.page.get_by_text(re.compile(r"comprar direto do atacado", re.I))
                card_atacado.wait_for(state="visible", timeout=3000)
                card_atacado.click(timeout=3000)
                print("  -> Modalidade 'Comprar direto do Atacado' selecionada.")
                self.page.wait_for_timeout(1000)
            except PlaywrightTimeoutError:
                pass

            try:
                input_cep = self.page.get_by_placeholder(re.compile(r"00000-000|cep", re.I))
                input_cep.wait_for(state="visible", timeout=4000)
                
                if cep not in input_cep.input_value():
                    input_cep.fill(cep)
                    input_cep.press("Tab")
                    self.page.wait_for_timeout(2000)
                    print("  -> CEP preenchido com sucesso.")
                else:
                    print("  -> CEP já preenchido pelo cache da sessão.")
            except PlaywrightTimeoutError:
                pass

            confirmado = False
            try:
                botao_confirmar_loja = self.page.get_by_role("button", name=re.compile(r"^confirmar$", re.I))
                if botao_confirmar_loja.is_visible(timeout=3000):
                    botao_confirmar_loja.click(timeout=3000)
                    confirmado = True
                    print("  -> Loja próxima confirmada via cache.")
            except Exception:
                pass

            if not confirmado:
                input_numero = None
                for seletor in (
                    self.page.get_by_placeholder(re.compile(r"n[uú]mero|^n[ºo°]", re.I)),
                    self.page.get_by_label(re.compile(r"n[uú]mero", re.I)),
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
                        self.page.get_by_role("button", name=re.compile(r"confirmar|continuar|salvar|avançar", re.I)).click(timeout=3000)
                        print("  -> Endereço completo confirmado.")
                    except Exception:
                        pass
                else:
                    try:
                        self.page.get_by_role("button", name=re.compile(r"confirmar|continuar|salvar|avançar", re.I)).click(timeout=3000)
                        print("  -> Confirmação genérica acionada.")
                    except Exception:
                        pass

            self.page.wait_for_timeout(2000)
            print("  -> Localização aplicada!")

        except Exception as e:
            self.salvar_evidencia_erro("definir_localizacao")
            raise e

    def buscar_produto(self, termo: str) -> dict:
        print(f"Buscando produto na VTEX: {termo}")
        try:
            campo_busca = self.page.get_by_placeholder(re.compile(r"busca|pesquis", re.I))
            campo_busca.click()
            
            # Limpa o campo caso haja pesquisa anterior
            campo_busca.fill("")
            campo_busca.fill(termo)

            with self.page.expect_response(
                lambda r: "operationName=ProductsQuery" in r.url and r.status == 200,
                timeout=15000,
            ) as info_resposta:
                campo_busca.press("Enter")

            dados = info_resposta.value.json()
            
            # Salva o JSON bruto na pasta debug para auditoria
            nome_arquivo = termo.replace(' ', '_').lower()
            caminho_saida = self.pasta_debug / f"raw_vtex_{nome_arquivo}.json"
            caminho_saida.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
            
            return dados
        except Exception as e:
            self.salvar_evidencia_erro(f"buscar_produto_{termo.replace(' ', '_')}")
            raise e


# ---------------------------------------------------------------------------
# Utilitários e Orquestração (Temporário até implementação da API/Banco)
# ---------------------------------------------------------------------------

def exportar_csv(produtos_filtrados, termo):
    nome_arquivo = termo.replace(' ', '_').lower()
    caminho_csv = Path(f"relatorio_{nome_arquivo}.csv")
    with open(caminho_csv, mode="w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.writer(arquivo, delimiter=";")
        escritor.writerow(["Produto", "Preço Atacado (R$)", "Score Relevância"])
        for p in produtos_filtrados:
            escritor.writerow([p["nome"], p["preco"], p["score"]])
    print(f"\n✅ Relatório exportado com sucesso para: {caminho_csv}")

def testar_busca_isolada(termo_dinamico: str, margem_corte: int = 60):
    with sync_playwright() as p:
        print(f"\n🚀 Iniciando o motor (Buscando: '{termo_dinamico}')...")
        browser = p.chromium.launch(headless=False, slow_mo=150)
        page = browser.new_page()

        try:
            # Instancia a loja seguindo o padrão Orientado a Objetos
            loja = Atacadao(page)
            loja.abrir_site()
            loja.definir_localizacao(CEP_TESTE, NUMERO_TESTE)
            
            dados = loja.buscar_produto(termo_dinamico)

            produtos = dados.get("data", {}).get("search", {}).get("products", {}).get("edges", [])
            
            print(f"\nResultados higienizados para '{termo_dinamico}' (Corte de Score: {margem_corte}):")
            print("-" * 65)
            
            lista_para_exportar = []
            for item in produtos:
                node = item.get("node", {})
                nome = str(node.get("name", "Nome indisponível")).strip()
                preco = node.get("offers", {}).get("lowPrice", 0.00)
                
                # Aplica o motor de Fuzzy Matching para validar a aderência do produto buscado
                score_similaridade = fuzz.token_set_ratio(termo_dinamico.lower(), nome.lower())
                
                if score_similaridade >= margem_corte:
                    print(f"  ✅ [Score: {score_similaridade}] {nome} | R$ {preco}")
                    lista_para_exportar.append({
                        "nome": nome, 
                        "preco": preco, 
                        "score": score_similaridade
                    })
                else:
                    print(f"  ❌ [Score: {score_similaridade}] Descartado: {nome}")
            
            print("-" * 65)
            print(f"Total de itens válidos encontrados: {len(lista_para_exportar)}")
            
            if lista_para_exportar:
                exportar_csv(lista_para_exportar, termo_dinamico)
            else:
                print(f"⚠️ A busca por '{termo_dinamico}' não retornou produtos relevantes.")

        except Exception as e:
            print(f"\n❌ Ocorreu um erro crítico na orquestração: {e}")
            traceback.print_exc()

        finally:
            print("Fechando o navegador...\n")
            browser.close()

if __name__ == "__main__":
    # Teste de execução passando um termo genérico para atestar a nova lógica dinâmica
    testar_busca_isolada("Café Pilão 500g", margem_corte=65)