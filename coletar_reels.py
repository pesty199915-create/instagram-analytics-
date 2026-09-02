import asyncio
import json
import re
import os
from datetime import datetime

import pandas as pd
from playwright.async_api import async_playwright


# ============================================================
# CONFIGURAÇÕES
# ============================================================

USUARIO = "reindeer.7441086"

QUANTIDADE_REELS = 200

ARQUIVO_JSON = f"{USUARIO}_reels.json"
ARQUIVO_CSV = f"{USUARIO}_reels.csv"
ARQUIVO_CONFIG = "config.json"

ROLAGENS_SEM_NOVOS = 4
MAX_ROLAGENS = 60

PAUSA_INICIAL = 2
PAUSA_ENTRE_ROLAGENS = 1.5

CONCORRENCIA_DATAS = 6


# ============================================================
# BRAVE
# ============================================================

BRAVE_PATHS = [
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
]

BRAVE_PATH = None

for caminho in BRAVE_PATHS:

    if os.path.exists(caminho):
        BRAVE_PATH = caminho
        break

if BRAVE_PATH is None:

    raise FileNotFoundError(
        "Brave não encontrado. Verifique se o Brave está instalado."
    )


# ============================================================
# PERFIL PERSISTENTE DO BRAVE
# ============================================================

PASTA_PERFIL_BRAVE = os.path.abspath(
    "brave_instagram_profile"
)


# ============================================================
# URL DO PERFIL
# ============================================================

URL_REELS = (
    f"https://www.instagram.com/"
    f"{USUARIO}/reels/"
)


# ============================================================
# CONVERSÃO DAS VISUALIZAÇÕES
# ============================================================

def converter_visualizacoes(texto):

    if not texto:
        return None

    texto = str(texto).strip().lower()
    texto = texto.replace("\xa0", " ")

    # --------------------------------------------------------
    # Valores com "mil"
    # --------------------------------------------------------

    if "mil" in texto:

        numero = texto.replace(
            "mil",
            ""
        ).strip()

        numero = numero.replace(
            ".",
            ""
        ).replace(
            ",",
            "."
        )

        try:

            return int(
                float(numero) * 1000
            )

        except Exception:

            return None

    # --------------------------------------------------------
    # Valores com "mi", "milhão" ou "milhões"
    # --------------------------------------------------------

    if (
        "mi" in texto
        or "milhão" in texto
        or "milhões" in texto
    ):

        numero = (
            texto
            .replace("milhões", "")
            .replace("milhão", "")
            .replace("mi", "")
            .strip()
        )

        numero = numero.replace(
            ".",
            ""
        ).replace(
            ",",
            "."
        )

        try:

            return int(
                float(numero) * 1_000_000
            )

        except Exception:

            return None

    # --------------------------------------------------------
    # NÚMEROS NORMAIS
    # --------------------------------------------------------

    try:

        # Exemplos:
        # 8.203   -> 8203
        # 12.900  -> 12900
        # 19.000  -> 19000

        if "." in texto and "," not in texto:

            partes = texto.split(".")

            if (
                len(partes) == 2
                and len(partes[1]) == 3
            ):

                return int(
                    partes[0] + partes[1]
                )

            # ------------------------------------------------
            # Correção do valor inflado
            #
            # 60.400.000 -> 60400
            # 68.900.000 -> 68900
            # 69.000.000 -> 69000
            # 86.100.000 -> 86100
            # ------------------------------------------------

            if len(partes) > 2:

                if all(
                    parte.isdigit()
                    and len(parte) == 3
                    for parte in partes[1:]
                ):

                    valor = int(
                        "".join(partes)
                    )

                    if partes[-1] == "000":

                        return valor // 1000

                    return valor

        # ----------------------------------------------------
        # Caso normal sem ponto
        # ----------------------------------------------------

        return int(
            texto
            .replace(".", "")
            .replace(",", "")
        )

    except Exception:

        return None


# ============================================================
# EXTRAIR NÚMEROS DO HTML
# ============================================================

def extrair_numero_regex(
    html,
    padroes
):

    for padrao in padroes:

        encontrados = re.findall(
            padrao,
            html,
            flags=re.IGNORECASE
        )

        if encontrados:

            for valor in encontrados:

                if isinstance(
                    valor,
                    tuple
                ):

                    valor = valor[0]

                try:

                    valor_limpo = (
                        str(valor)
                        .replace(",", "")
                        .replace(".", "")
                    )

                    return int(
                        valor_limpo
                    )

                except Exception:

                    continue

    return None


# ============================================================
# TIMESTAMP
# ============================================================

def extrair_timestamp_do_texto(
    texto
):

    if not texto:
        return None

    padroes = [

        r'"taken_at_timestamp"\s*:\s*(\d+)',
        r'"taken_at"\s*:\s*(\d+)',
        r'"created_at"\s*:\s*(\d+)',
        r'"publish_time"\s*:\s*(\d+)',
        r'"published_at"\s*:\s*(\d+)',
        r'"published_time"\s*:\s*(\d+)',
        r'"datePublished"\s*:\s*"([^"]+)"',
        r'"uploadDate"\s*:\s*"([^"]+)"'

    ]

    for padrao in padroes:

        encontrados = re.findall(
            padrao,
            texto,
            flags=re.IGNORECASE
        )

        for valor in encontrados:

            if isinstance(
                valor,
                tuple
            ):

                valor = valor[0]

            valor = str(
                valor
            ).strip()

            # ------------------------------------------------
            # Timestamp Unix
            # ------------------------------------------------

            if valor.isdigit():

                try:

                    timestamp = int(
                        valor
                    )

                    if (
                        1_000_000_000
                        <= timestamp
                        <= 4_000_000_000
                    ):

                        return timestamp

                except Exception:

                    pass

            # ------------------------------------------------
            # ISO
            # ------------------------------------------------

            try:

                texto_data = valor.replace(
                    "Z",
                    "+00:00"
                )

                dt = datetime.fromisoformat(
                    texto_data
                )

                return int(
                    dt.timestamp()
                )

            except Exception:

                pass

    return None


# ============================================================
# TIMESTAMP -> DATA/HORA
# ============================================================

def timestamp_para_dados(
    timestamp
):

    if not timestamp:

        return {
            "data": None,
            "hora": None,
            "dia": None
        }

    try:

        dt = datetime.fromtimestamp(
            timestamp
        )

        dias = [

            "segunda-feira",
            "terça-feira",
            "quarta-feira",
            "quinta-feira",
            "sexta-feira",
            "sábado",
            "domingo"

        ]

        return {

            "data": dt.strftime(
                "%d/%m/%Y"
            ),

            "hora": dt.strftime(
                "%H:%M:%S"
            ),

            "dia": dias[
                dt.weekday()
            ]

        }

    except Exception:

        return {

            "data": None,
            "hora": None,
            "dia": None

        }


# ============================================================
# VIEWS DENTRO DO HTML DO REEL
# ============================================================

def extrair_views_html(
    html
):

    padroes = [

        r'"play_count"\s*:\s*(\d+)',
        r'"view_count"\s*:\s*(\d+)',
        r'"video_view_count"\s*:\s*(\d+)',
        r'"ig_play_count"\s*:\s*(\d+)',
        r'"video_play_count"\s*:\s*(\d+)',
        r'"playCount"\s*:\s*(\d+)'

    ]

    return extrair_numero_regex(
        html,
        padroes
    )


# ============================================================
# VIEWS DOS CARDS
# ============================================================

async def extrair_views_cards(
    page
):

    elementos = page.locator(
        'svg[aria-label="Ver ícone de contagem"]'
    )

    try:

        quantidade = await elementos.count()

    except Exception:

        return []

    if quantidade == 0:

        return []

    resultado = await elementos.evaluate_all(
        """
        svgs => {

            function distanciaEntreRetangulos(a, b) {

                const ax = a.left + a.width / 2;
                const ay = a.top + a.height / 2;

                const bx = b.left + b.width / 2;
                const by = b.top + b.height / 2;

                return Math.sqrt(
                    Math.pow(ax - bx, 2) +
                    Math.pow(ay - by, 2)
                );
            }

            function areaIntersecao(a, b) {

                const esquerda = Math.max(
                    a.left,
                    b.left
                );

                const topo = Math.max(
                    a.top,
                    b.top
                );

                const direita = Math.min(
                    a.right,
                    b.right
                );

                const baixo = Math.min(
                    a.bottom,
                    b.bottom
                );

                const largura = Math.max(
                    0,
                    direita - esquerda
                );

                const altura = Math.max(
                    0,
                    baixo - topo
                );

                return largura * altura;
            }

            const anchors = Array.from(
                document.querySelectorAll(
                    'a[href*="/reel/"]'
                )
            );

            const saida = [];

            for (const svg of svgs) {

                let texto = null;
                let noTexto = null;
                let atual = svg;

                // ------------------------------------------------
                // Procura o texto de visualizações
                // ------------------------------------------------

                for (
                    let nivel = 0;
                    nivel < 8 && atual;
                    nivel++
                ) {

                    const spans = Array.from(
                        atual.querySelectorAll
                            ? atual.querySelectorAll("span")
                            : []
                    );

                    for (const span of spans) {

                        const t = (
                            span.innerText || ""
                        ).trim();

                        if (
                            /\\d/.test(t) &&
                            t.length < 100
                        ) {

                            texto = t;
                            noTexto = span;
                            break;
                        }
                    }

                    if (texto) {
                        break;
                    }

                    atual = atual.parentElement;
                }

                // ------------------------------------------------
                // Fallback
                // ------------------------------------------------

                if (!texto) {

                    atual = svg;

                    for (
                        let nivel = 0;
                        nivel < 8 && atual;
                        nivel++
                    ) {

                        const bruto = (
                            atual.innerText || ""
                        ).trim();

                        if (bruto) {

                            const linhas = bruto
                                .split("\\n")
                                .map(x => x.trim())
                                .filter(Boolean);

                            for (
                                const linha of linhas
                            ) {

                                if (
                                    /\\d/.test(linha) &&
                                    linha.length < 100
                                ) {

                                    texto = linha;
                                    noTexto = atual;
                                    break;
                                }
                            }
                        }

                        if (texto) {
                            break;
                        }

                        atual = atual.parentElement;
                    }
                }

                if (!texto) {
                    continue;
                }

                // ------------------------------------------------
                // Retângulo do SVG
                // ------------------------------------------------

                const rectSvg =
                    svg.getBoundingClientRect();

                // ------------------------------------------------
                // Procura o Reel mais próximo
                // ------------------------------------------------

                let melhor = null;

                let melhorPontuacao =
                    Infinity;

                for (
                    const anchor of anchors
                ) {

                    const rectAnchor =
                        anchor.getBoundingClientRect();

                    const intersecao =
                        areaIntersecao(
                            rectSvg,
                            rectAnchor
                        );

                    const distancia =
                        distanciaEntreRetangulos(
                            rectSvg,
                            rectAnchor
                        );

                    let pontuacao =
                        distancia;

                    if (
                        intersecao > 0
                    ) {

                        pontuacao -= 100000;
                    }

                    if (
                        pontuacao <
                        melhorPontuacao
                    ) {

                        melhorPontuacao =
                            pontuacao;

                        melhor = anchor;
                    }
                }

                // ------------------------------------------------
                // Fallback subindo no DOM
                // ------------------------------------------------

                if (!melhor) {

                    atual = svg;

                    for (
                        let nivel = 0;
                        nivel < 10 && atual;
                        nivel++
                    ) {

                        const anchor =
                            atual.closest
                                ? atual.closest(
                                    'a[href*="/reel/"]'
                                )
                                : null;

                        if (anchor) {

                            melhor = anchor;
                            break;
                        }

                        atual =
                            atual.parentElement;
                    }
                }

                if (
                    melhor &&
                    texto
                ) {

                    saida.push({

                        url: melhor.href,

                        texto_views: texto

                    });
                }
            }

            return saida;
        }
        """
    )

    return resultado


# ============================================================
# VERIFICAR SESSÃO E IR DIRETO PARA REELS
# ============================================================

async def verificar_login(
    page
):

    print()
    print("=" * 70)
    print("ABRINDO REELS DIRETAMENTE")
    print("=" * 70)
    print()

    print(
        f"Perfil alvo: @{USUARIO}"
    )

    print(
        f"URL: {URL_REELS}"
    )

    print()

    try:

        # ----------------------------------------------------
        # VAI DIRETO PARA O REELS
        # ----------------------------------------------------

        await page.goto(
            URL_REELS,
            wait_until="domcontentloaded",
            timeout=60000
        )

        # Pequena espera para o Instagram montar o DOM
        await asyncio.sleep(
            PAUSA_INICIAL
        )

        url_atual = page.url.lower()

        # ----------------------------------------------------
        # LOGIN NECESSÁRIO
        # ----------------------------------------------------

        if (
            "/accounts/login" in url_atual
            or "/login" in url_atual
        ):

            print()
            print(
                "⚠ Sessão do Instagram não encontrada."
            )

            print()
            print(
                "Faça o login manualmente no Brave."
            )

            print(
                "Depois volte para o terminal."
            )

            print()

            await asyncio.to_thread(
                input,
                ">>> Após fazer login, pressione ENTER..."
            )

            print()
            print(
                "✓ ENTER recebido."
            )

            print(
                "Abrindo novamente o perfil..."
            )

            print()

            # ------------------------------------------------
            # Depois do login vai novamente DIRETO para reels
            # ------------------------------------------------

            await page.goto(
                URL_REELS,
                wait_until="domcontentloaded",
                timeout=60000
            )

            await asyncio.sleep(
                PAUSA_INICIAL
            )

            url_atual = page.url.lower()

            if (
                "/accounts/login" in url_atual
                or "/login" in url_atual
            ):

                print()
                print(
                    "✗ O Instagram ainda está solicitando login."
                )

                print()

                return False

        # ----------------------------------------------------
        # VERIFICA SE ESTAMOS NO PERFIL
        # ----------------------------------------------------

        if (
            USUARIO.lower()
            not in url_atual
        ):

            print()
            print(
                f"⚠ URL inesperada:"
            )

            print(
                page.url
            )

            print()

        # ----------------------------------------------------
        # SUCESSO
        # ----------------------------------------------------

        print()
        print(
            f"✓ Página aberta diretamente:"
        )

        print(
            page.url
        )

        print()

        print(
            "✓ Sessão disponível."
        )

        print(
            "✓ Iniciando coleta automaticamente."
        )

        print()

        return True

    except Exception as e:

        print()
        print(
            f"⚠ Erro ao abrir o perfil:"
        )

        print(
            e
        )

        print()

        return False


# ============================================================
# COLETAR LINKS DOS REELS + VIEWS DOS CARDS
# ============================================================

async def coletar_links(
    page
):

    print()
    print("=" * 70)
    print("COLETANDO REELS")
    print("=" * 70)
    print()

    print(
        f"Página atual: {page.url}"
    )

    print()

    reels = {}

    sem_novos = 0

    for rodada in range(
        1,
        MAX_ROLAGENS + 1
    ):

        # ----------------------------------------------------
        # Links dos Reels no DOM
        # ----------------------------------------------------

        links = await page.locator(
            'a[href*="/reel/"]'
        ).evaluate_all(
            """
            links => links.map(
                a => a.href
            )
            """
        )

        novos = 0

        for link in links:

            link = link.split("?")[0]

            if "/reel/" not in link:

                continue

            if link not in reels:

                reels[link] = {

                    "url": link,

                    "views_card": None

                }

                novos += 1

        # ----------------------------------------------------
        # Views dos cards
        # ----------------------------------------------------

        views_cards = await extrair_views_cards(
            page
        )

        for item in views_cards:

            url = item[
                "url"
            ].split("?")[0]

            texto_views = item[
                "texto_views"
            ]

            valor = converter_visualizacoes(
                texto_views
            )

            if url in reels:

                reels[url][
                    "views_card"
                ] = valor

        total = len(
            reels
        )

        # ----------------------------------------------------
        # Quantidade com views
        # ----------------------------------------------------

        quantidade_views = sum(

            1

            for item in reels.values()

            if item[
                "views_card"
            ] is not None

        )

        print(

            f"Rolagem {rodada:02d}/"
            f"{MAX_ROLAGENS} | "
            f"Total: {total} | "
            f"Novos: {novos} | "
            f"Views nos cards: "
            f"{quantidade_views}"

        )

        # ----------------------------------------------------
        # Exemplos
        # ----------------------------------------------------

        exemplos = [

            item

            for item in reels.values()

            if item[
                "views_card"
            ] is not None

        ][-5:]

        for item in exemplos:

            views = item[
                "views_card"
            ]

            if views is not None:

                views_formatado = (
                    f"{views:,}"
                    .replace(",", ".")
                )

            else:

                views_formatado = "N/A"

            print(

                f"   ✓ "
                f"{views_formatado} | "
                f"{item['url']}"

            )

        print()

        # ----------------------------------------------------
        # Limite atingido
        # ----------------------------------------------------

        if total >= QUANTIDADE_REELS:

            print(

                f"Limite de "
                f"{QUANTIDADE_REELS} "
                f"Reels atingido."

            )

            break

        # ----------------------------------------------------
        # Controle sem novos
        # ----------------------------------------------------

        if novos == 0:

            sem_novos += 1

        else:

            sem_novos = 0

        if sem_novos >= ROLAGENS_SEM_NOVOS:

            print(
                "Não apareceram novos Reels "
                "nas últimas rolagens."
            )

            break

        # ----------------------------------------------------
        # Rolar
        # ----------------------------------------------------

        await page.evaluate(
            """
            () => {

                window.scrollBy({

                    top: 3000,

                    behavior: "smooth"

                });

            }
            """
        )

        await asyncio.sleep(
            PAUSA_ENTRE_ROLAGENS
        )

    # --------------------------------------------------------
    # Limita quantidade
    # --------------------------------------------------------

    reels_lista = list(
        reels.values()
    )[:QUANTIDADE_REELS]

    print()
    print(
        f"Total final de Reels coletados: "
        f"{len(reels_lista)}"
    )

    print()

    return reels_lista


# ============================================================
# EXTRAIR DATA/HORA DO REEL
# ============================================================

async def extrair_data_reel(
    page,
    url
):

    try:

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        await page.wait_for_timeout(
            1200
        )

        # ----------------------------------------------------
        # 1. TIME
        # ----------------------------------------------------

        times = await page.locator(
            "time"
        ).evaluate_all(
            """
            elements => elements.map(el => ({

                datetime:
                    el.getAttribute("datetime"),

                texto:
                    el.innerText

            }))
            """
        )

        for item in times:

            datetime_value = item.get(
                "datetime"
            )

            if datetime_value:

                timestamp = extrair_timestamp_do_texto(
                    datetime_value
                )

                if timestamp:

                    return timestamp

        # ----------------------------------------------------
        # 2. META
        # ----------------------------------------------------

        metas = await page.locator(
            'meta[property="article:published_time"], '
            'meta[property="og:published_time"], '
            'meta[name="publish_date"], '
            'meta[name="date"]'
        ).evaluate_all(
            """
            elements => elements.map(
                el => el.getAttribute("content")
            )
            """
        )

        for valor in metas:

            timestamp = extrair_timestamp_do_texto(
                str(valor)
            )

            if timestamp:

                return timestamp

        # ----------------------------------------------------
        # 3. JSON-LD
        # ----------------------------------------------------

        json_ld = await page.locator(
            'script[type="application/ld+json"]'
        ).all_text_contents()

        for texto in json_ld:

            timestamp = extrair_timestamp_do_texto(
                texto
            )

            if timestamp:

                return timestamp

        # ----------------------------------------------------
        # 4. HTML
        # ----------------------------------------------------

        html = await page.content()

        timestamp = extrair_timestamp_do_texto(
            html
        )

        if timestamp:

            return timestamp

        # ----------------------------------------------------
        # 5. SCRIPTS
        # ----------------------------------------------------

        scripts = await page.locator(
            "script"
        ).all_text_contents()

        for script in scripts:

            timestamp = extrair_timestamp_do_texto(
                script
            )

            if timestamp:

                return timestamp

    except Exception as e:

        print(
            f"   ⚠ Erro na data: "
            f"{url} -> {e}"
        )

    return None


# ============================================================
# TRABALHADOR DE DATAS
# ============================================================

async def trabalhador_datas(
    worker_id,
    fila,
    resultados
):

    async with async_playwright() as pw:

        browser = await pw.chromium.launch(

            headless=True,

            executable_path=BRAVE_PATH

        )

        context = await browser.new_context(

            viewport={
                "width": 1280,
                "height": 800
            },

            locale="pt-BR",

            timezone_id="America/Sao_Paulo"

        )

        page = await context.new_page()

        while True:

            try:

                item = fila.get_nowait()

            except asyncio.QueueEmpty:

                break

            url = item[
                "url"
            ]

            timestamp = await extrair_data_reel(

                page,

                url

            )

            resultados[url] = timestamp

            if timestamp:

                dados = timestamp_para_dados(
                    timestamp
                )

                print(

                    f"   ✓ [{worker_id}] "
                    f"{dados['data']} "
                    f"{dados['hora']} | "
                    f"{url}"

                )

            else:

                print(

                    f"   ✗ [{worker_id}] "
                    f"Data não encontrada | "
                    f"{url}"

                )

            fila.task_done()

        await browser.close()


# ============================================================
# COLETAR DATAS EM PARALELO
# ============================================================

async def coletar_datas_em_paralelo(
    reels
):

    print()
    print("=" * 70)
    print(
        "BUSCANDO DATA/HORA DOS REELS"
    )
    print("=" * 70)
    print()

    fila = asyncio.Queue()

    for reel in reels:

        await fila.put(
            reel
        )

    resultados = {}

    trabalhadores = []

    quantidade = min(
        CONCORRENCIA_DATAS,
        len(reels)
    )

    for i in range(
        quantidade
    ):

        tarefa = asyncio.create_task(

            trabalhador_datas(

                i + 1,

                fila,

                resultados

            )

        )

        trabalhadores.append(
            tarefa
        )

    await fila.join()

    await asyncio.gather(

        *trabalhadores,

        return_exceptions=True

    )

    encontrados = sum(

        1

        for valor in resultados.values()

        if valor

    )

    print()

    print(

        f"Datas encontradas: "
        f"{encontrados}/{len(reels)}"

    )

    return resultados


# ============================================================
# APLICAR DATAS
# ============================================================

def aplicar_datas(
    reels,
    timestamps
):

    for reel in reels:

        url = reel[
            "url"
        ]

        timestamp = timestamps.get(
            url
        )

        if timestamp:

            dados = timestamp_para_dados(
                timestamp
            )

            reel["data"] = dados[
                "data"
            ]

            reel["hora"] = dados[
                "hora"
            ]

            reel["dia"] = dados[
                "dia"
            ]

        else:

            reel["data"] = None
            reel["hora"] = None
            reel["dia"] = None


# ============================================================
# SALVAR JSON
# ============================================================

def salvar_json(
    dados
):

    estrutura = {

        "perfil": USUARIO,

        "atualizado_em":
            datetime.now().isoformat(),

        "total":
            len(dados),

        "reels":
            dados

    }

    with open(

        ARQUIVO_JSON,

        "w",

        encoding="utf-8"

    ) as arquivo:

        json.dump(

            estrutura,

            arquivo,

            ensure_ascii=False,

            indent=2

        )

    print(

        f"JSON salvo em: "
        f"{ARQUIVO_JSON}"

    )


# ============================================================
# SALVAR CSV
# ============================================================

def salvar_csv(
    dados
):

    df = pd.DataFrame(
        dados
    )

    colunas = [

        "ordem",
        "data",
        "hora",
        "dia",
        "views",
        "curtidas",
        "comentarios",
        "url",
        "origem_views"

    ]

    df = df.reindex(
        columns=colunas
    )

    df.to_csv(

        ARQUIVO_CSV,

        index=False,

        encoding="utf-8-sig"

    )

    print(

        f"CSV salvo em: "
        f"{ARQUIVO_CSV}"

    )


# ============================================================
# SALVAR CONFIG
# ============================================================

def salvar_config():

    # --------------------------------------------------------
    # Carrega o config.json existente
    # --------------------------------------------------------

    if os.path.exists(
        ARQUIVO_CONFIG
    ):

        try:

            with open(

                ARQUIVO_CONFIG,

                "r",

                encoding="utf-8"

            ) as arquivo:

                config = json.load(
                    arquivo
                )

        except Exception:

            config = {}

    else:

        config = {}

    # --------------------------------------------------------
    # Garante que exista "contas"
    # --------------------------------------------------------

    contas = config.get(
        "contas",
        []
    )

    if not isinstance(
        contas,
        list
    ):

        contas = []

    # --------------------------------------------------------
    # Remove a conta atual caso já exista
    # --------------------------------------------------------

    contas = [

        conta

        for conta in contas

        if conta.get(
            "perfil",
            ""
        ).lower() != USUARIO.lower()

    ]

    # --------------------------------------------------------
    # Adiciona a conta atual
    # --------------------------------------------------------

    contas.append({

        "perfil":
            USUARIO,

        "arquivo_json":
            ARQUIVO_JSON,

        "arquivo_csv":
            ARQUIVO_CSV

    })

    # --------------------------------------------------------
    # Ordena pelo nome
    # --------------------------------------------------------

    contas.sort(

        key=lambda conta:
        conta.get(
            "perfil",
            ""
        ).lower()

    )

    # --------------------------------------------------------
    # Monta config
    # --------------------------------------------------------

    novo_config = {

        "contas":
            contas

    }

    # --------------------------------------------------------
    # Salva
    # --------------------------------------------------------

    with open(

        ARQUIVO_CONFIG,

        "w",

        encoding="utf-8"

    ) as arquivo:

        json.dump(

            novo_config,

            arquivo,

            ensure_ascii=False,

            indent=2

        )

    print(

        f"Config atualizado: "
        f"{len(contas)} conta(s)"

    )


# ============================================================
# MAIN
# ============================================================

async def main():

    print()
    print("=" * 70)
    print(
        "INSTAGRAM REELS SCRAPER"
    )
    print("=" * 70)
    print()

    print(
        f"Perfil alvo: @{USUARIO}"
    )

    print(
        f"Quantidade desejada: "
        f"{QUANTIDADE_REELS}"
    )

    print(
        f"URL direta: "
        f"{URL_REELS}"
    )

    print(
        f"Brave: {BRAVE_PATH}"
    )

    print(
        f"Perfil persistente: "
        f"{PASTA_PERFIL_BRAVE}"
    )

    print()

    async with async_playwright() as p:

        # ====================================================
        # ABRIR BRAVE COM PERFIL PERSISTENTE
        # ====================================================

        print(
            "Abrindo Brave com perfil persistente..."
        )

        print()

        context = await p.chromium.launch_persistent_context(

            user_data_dir=
                PASTA_PERFIL_BRAVE,

            headless=False,

            executable_path=
                BRAVE_PATH,

            viewport={

                "width": 1400,

                "height": 900

            },

            locale="pt-BR",

            timezone_id=
                "America/Sao_Paulo"

        )

        # ====================================================
        # ORGANIZAR ABAS
        # ====================================================

        paginas = context.pages

        # ----------------------------------------------------
        # Fecha abas extras
        # ----------------------------------------------------

        for pagina in paginas[1:]:

            try:

                await pagina.close()

            except Exception:

                pass

        # ----------------------------------------------------
        # Usa primeira aba
        # ----------------------------------------------------

        if paginas:

            page = paginas[0]

            print(
                "✓ Usando uma única aba do Brave."
            )

        else:

            page = await context.new_page()

            print(
                "✓ Criando uma única aba."
            )

        print()

        # ====================================================
        # VAI DIRETO PARA O REELS
        # ====================================================

        login_ok = await verificar_login(
            page
        )

        if not login_ok:

            print(
                "Não foi possível acessar o perfil."
            )

            await context.close()

            return

        # ====================================================
        # COLETA DOS CARDS
        # ====================================================

        reels = await coletar_links(
            page
        )

        # ----------------------------------------------------
        # Fecha Brave visual
        # ----------------------------------------------------

        await context.close()

        # ====================================================
        # DATAS EM PARALELO
        # ====================================================

        timestamps = await coletar_datas_em_paralelo(
            reels
        )

        aplicar_datas(
            reels,
            timestamps
        )

        # ====================================================
        # MONTAR RESULTADO FINAL
        # ====================================================

        dados_finais = []

        # ----------------------------------------------------
        # Se necessário, abre um navegador headless apenas
        # para buscar views que não vieram dos cards.
        # ----------------------------------------------------

        browser_reel = None
        context_reel = None
        page_reel = None

        for indice, info in enumerate(

            reels,

            start=1

        ):

            views_card = info.get(
                "views_card"
            )

            views_reel = None

            # ------------------------------------------------
            # Se não houver view do card
            # ------------------------------------------------

            if views_card is None:

                try:

                    # Abre apenas uma vez
                    # e reutiliza para todos os Reels.

                    if browser_reel is None:

                        browser_reel = await p.chromium.launch(

                            headless=True,

                            executable_path=
                                BRAVE_PATH

                        )

                        context_reel = await browser_reel.new_context(

                            locale="pt-BR",

                            timezone_id=
                                "America/Sao_Paulo"

                        )

                        page_reel = await context_reel.new_page()

                    await page_reel.goto(

                        info["url"],

                        wait_until=
                            "domcontentloaded",

                        timeout=60000

                    )

                    await asyncio.sleep(
                        1
                    )

                    html = await page_reel.content()

                    views_reel = extrair_views_html(
                        html
                    )

                except Exception:

                    views_reel = None

            # ------------------------------------------------
            # Prioridade:
            #
            # 1. CARD
            # 2. REEL
            # ------------------------------------------------

            if views_card is not None:

                views = views_card

                origem_views = "card"

            else:

                views = views_reel

                origem_views = "reel"

            dados_finais.append({

                "ordem":
                    indice,

                "url":
                    info["url"],

                "data":
                    info.get(
                        "data"
                    ),

                "hora":
                    info.get(
                        "hora"
                    ),

                "dia":
                    info.get(
                        "dia"
                    ),

                "views":
                    views,

                "curtidas":
                    None,

                "comentarios":
                    None,

                "origem_views":
                    origem_views

            })

        # ----------------------------------------------------
        # Fecha navegador auxiliar
        # ----------------------------------------------------

        if browser_reel is not None:

            try:

                await browser_reel.close()

            except Exception:

                pass

        # ====================================================
        # SALVAR
        # ====================================================

        print()

        print("=" * 70)

        print(
            "SALVANDO RESULTADOS"
        )

        print("=" * 70)

        print()

        salvar_json(
            dados_finais
        )

        salvar_csv(
            dados_finais
        )

        salvar_config()

        # ====================================================
        # RESUMO
        # ====================================================

        quantidade_card = sum(

            1

            for item in dados_finais

            if item[
                "origem_views"
            ] == "card"

        )

        quantidade_reel = sum(

            1

            for item in dados_finais

            if item[
                "origem_views"
            ] == "reel"

        )

        quantidade_datas = sum(

            1

            for item in dados_finais

            if item.get(
                "data"
            )

        )

        print()

        print("=" * 70)

        print(
            "FINALIZADO"
        )

        print("=" * 70)

        print()

        print(

            f"Reels processados: "
            f"{len(dados_finais)}"

        )

        print(

            f"Views vindas dos cards: "
            f"{quantidade_card}"

        )

        print(

            f"Views vindas do Reel: "
            f"{quantidade_reel}"

        )

        print(

            f"Datas encontradas: "
            f"{quantidade_datas}"

        )

        print()

        print(

            f"JSON: "
            f"{ARQUIVO_JSON}"

        )

        print(

            f"CSV: "
            f"{ARQUIVO_CSV}"

        )

        print(

            f"Config: "
            f"{ARQUIVO_CONFIG}"

        )

        print()


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )