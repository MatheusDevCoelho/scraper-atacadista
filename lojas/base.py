from datetime import datetime
from pathlib import Path

from thefuzz import fuzz

PASTA_DEBUG = Path("debug")


class LojaBase:
    """
    Interface comum a todas as lojas de atacarejo suportadas.
    Cada loja implementa sua própria lógica de UI (abrir_site,
    definir_localizacao, buscar_produto) e como extrair produtos
    do formato bruto que a sua API/HTML retorna. A higienização
    (filtro fuzzy) é compartilhada por todas, uma vez normalizado
    para {"nome": str, "preco": float | None}.
    """

    def __init__(self, page):
        self.page = page
        self.pasta_debug = PASTA_DEBUG
        self.pasta_debug.mkdir(exist_ok=True)

    async def salvar_evidencia_erro(self, contexto: str):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefixo = f"{contexto}_{timestamp}"
        caminho_img = self.pasta_debug / f"{prefixo}.png"
        caminho_html = self.pasta_debug / f"{prefixo}.html"

        print(f"\n[DEBUG] ⚠️ Falha detectada no bloco: '{contexto}'")
        try:
            await self.page.screenshot(path=str(caminho_img))
            conteudo = await self.page.content()
            caminho_html.write_text(conteudo, encoding="utf-8")
        except Exception as e:
            print(f"  -> Falha ao tentar salvar evidências: {e}\n")

    async def abrir_site(self):
        raise NotImplementedError

    async def definir_localizacao(self, cep: str, numero: str):
        raise NotImplementedError

    async def buscar_produto(self, termo: str) -> dict:
        """Deve retornar o payload bruto (JSON/dict) retornado pela loja."""
        raise NotImplementedError

    def extrair_produtos_brutos(self, dados: dict) -> list[dict]:
        """
        Deve normalizar o payload bruto específico da loja para uma lista
        de {"nome": str, "preco": float | None}. Não deve fazer chamadas
        de rede — só parsing de um dict já em memória.
        """
        raise NotImplementedError


def higienizar_produtos(
    produtos_brutos: list[dict], termo: str, score_minimo: int = 60
) -> list[dict]:
    """
    Filtra e ordena produtos por similaridade fuzzy com o termo buscado.
    Genérica: não sabe nem precisa saber de qual loja vieram os dados.

    score_minimo é um ponto de partida (0-100) — ajuste empírico depois
    de ver resultados reais; termos muito genéricos podem precisar de
    um score mais alto para evitar falsos positivos.
    """
    resultado = []
    for produto in produtos_brutos:
        nome = produto.get("nome", "")
        if not nome:
            continue
        score = fuzz.token_set_ratio(termo, nome)
        if score >= score_minimo:
            resultado.append({**produto, "score": score})

    resultado.sort(key=lambda p: p["score"], reverse=True)
    return resultado
