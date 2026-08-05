import re

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .base import LojaBase


class Atacadao(LojaBase):

    async def abrir_site(self):
        try:
            await self.page.goto("https://www.atacadao.com.br", wait_until="domcontentloaded")
            await self._aceitar_cookies()
        except Exception as e:
            await self.salvar_evidencia_erro("abrir_site_atacadao")
            raise e

    async def _aceitar_cookies(self):
        try:
            botao = self.page.get_by_role("button", name=re.compile(r"aceit|concord", re.I))
            await botao.click(timeout=5000)
        except PlaywrightTimeoutError:
            pass

    async def definir_localizacao(self, cep: str, numero: str):
        try:
            try:
                await self.page.get_by_role(
                    "button", name=re.compile(r"informar localiza", re.I)
                ).click(timeout=4000)
            except PlaywrightTimeoutError:
                pass

            try:
                card_atacado = self.page.get_by_text(re.compile(r"comprar direto do atacado", re.I))
                await card_atacado.wait_for(state="visible", timeout=3000)
                await card_atacado.click(timeout=3000)
                await self.page.wait_for_timeout(1000)
            except PlaywrightTimeoutError:
                pass

            try:
                input_cep = self.page.get_by_placeholder(re.compile(r"00000-000|cep", re.I))
                await input_cep.wait_for(state="visible", timeout=4000)
                valor_atual = await input_cep.input_value()
                if cep not in valor_atual:
                    await input_cep.fill(cep)
                    await input_cep.press("Tab")
                    await self.page.wait_for_timeout(2000)
            except PlaywrightTimeoutError:
                pass

            confirmado = False
            try:
                botao_confirmar_loja = self.page.get_by_role(
                    "button", name=re.compile(r"^confirmar$", re.I)
                )
                if await botao_confirmar_loja.is_visible():
                    await botao_confirmar_loja.click(timeout=3000)
                    confirmado = True
            except Exception:
                pass

            if not confirmado:
                input_numero = None
                for seletor in (
                    self.page.get_by_placeholder(re.compile(r"n[uú]mero|^n[ºo°]", re.I)),
                    self.page.get_by_label(re.compile(r"n[uú]mero", re.I)),
                ):
                    try:
                        await seletor.wait_for(state="visible", timeout=2000)
                        input_numero = seletor
                        break
                    except PlaywrightTimeoutError:
                        continue

                if input_numero:
                    await input_numero.fill(numero)
                    try:
                        await self.page.get_by_role(
                            "button", name=re.compile(r"confirmar|continuar|salvar|avançar", re.I)
                        ).click(timeout=3000)
                    except Exception:
                        pass
                else:
                    try:
                        await self.page.get_by_role(
                            "button", name=re.compile(r"confirmar|continuar|salvar|avançar", re.I)
                        ).click(timeout=3000)
                    except Exception:
                        pass

            await self.page.wait_for_timeout(2000)
        except Exception as e:
            await self.salvar_evidencia_erro("definir_localizacao")
            raise e

    async def buscar_produto(self, termo: str) -> dict:
        try:
            campo_busca = self.page.get_by_placeholder(re.compile(r"busca|pesquis", re.I))
            await campo_busca.click()
            await campo_busca.fill("")
            await campo_busca.fill(termo)

            async with self.page.expect_response(
                lambda r: "operationName=ProductsQuery" in r.url and r.status == 200,
                timeout=15000,
            ) as info_resposta:
                await campo_busca.press("Enter")

            resposta = await info_resposta.value
            dados = await resposta.json()
            return dados
        except Exception as e:
            await self.salvar_evidencia_erro(f"buscar_produto_{termo.replace(' ', '_')}")
            raise e

    def extrair_produtos_brutos(self, dados: dict) -> list[dict]:
        """
        Normaliza o JSON do GraphQL do Atacadão (VTEX IO) para o formato
        comum {"nome", "preco"} usado pela higienização genérica.
        """
        produtos = (
            dados.get("data", {})
            .get("search", {})
            .get("products", {})
            .get("edges", [])
        )

        resultado = []
        for item in produtos:
            node = item.get("node", {})
            nome = str(node.get("name", "")).strip()
            preco = node.get("offers", {}).get("lowPrice")
            if nome:
                resultado.append({"nome": nome, "preco": preco})
        return resultado
