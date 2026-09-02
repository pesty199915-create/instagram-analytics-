export default async function handler(req, res) {
  // ================================
  // CONFIGURAÇÃO
  // ================================

  const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
  const GITHUB_OWNER = process.env.GITHUB_OWNER || "pesty199915-create";
  const GITHUB_REPO = process.env.GITHUB_REPO || "instagram-analytics-";
  const GITHUB_BRANCH = process.env.GITHUB_BRANCH || "main";

  // ================================
  // CORS
  // ================================

  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");

  if (req.method === "OPTIONS") {
    return res.status(200).json({ ok: true });
  }

  // ================================
  // TESTE DA API
  // ================================

  if (req.method === "GET") {
    return res.status(200).json({
      ok: true,
      message: "Instagram Analytics API funcionando",
      github_configurado: !!GITHUB_TOKEN
    });
  }

  // ================================
  // SOMENTE POST
  // ================================

  if (req.method !== "POST") {
    return res.status(405).json({
      ok: false,
      erro: "Método não permitido"
    });
  }

  if (!GITHUB_TOKEN) {
    return res.status(500).json({
      ok: false,
      erro: "GITHUB_TOKEN não configurado na Vercel"
    });
  }

  try {
    const body = req.body;

    // ================================
    // VALIDAR DADOS
    // ================================

    if (!body || typeof body !== "object") {
      return res.status(400).json({
        ok: false,
        erro: "Corpo da requisição inválido"
      });
    }

    const perfil =
      body.perfil ||
      body.usuario ||
      body.username ||
      body.user;

    if (!perfil || typeof perfil !== "string") {
      return res.status(400).json({
        ok: false,
        erro: "Perfil não informado"
      });
    }

    // Remove caracteres perigosos do nome do arquivo
    const perfilLimpo = perfil
      .trim()
      .replace(/[^a-zA-Z0-9._-]/g, "");

    if (!perfilLimpo) {
      return res.status(400).json({
        ok: false,
        erro: "Perfil inválido"
      });
    }

    // ================================
    // PEGAR REELS
    // ================================

    let reels = [];

    if (Array.isArray(body.reels)) {
      reels = body.reels;
    } else if (Array.isArray(body.dados)) {
      reels = body.dados;
    }

    if (!reels.length) {
      return res.status(400).json({
        ok: false,
        erro: "Nenhum reel recebido"
      });
    }

    // ================================
    // NORMALIZAR REELS
    // ================================

    reels = reels.map((reel, index) => {
      return {
        ordem: Number(reel.ordem) || index + 1,

        url: reel.url || "",

        data: reel.data || "",

        hora: reel.hora || "",

        dia: reel.dia || "",

        views:
          reel.views === null ||
          reel.views === undefined ||
          reel.views === ""
            ? null
            : Number(reel.views),

        curtidas:
          reel.curtidas === null ||
          reel.curtidas === undefined ||
          reel.curtidas === ""
            ? null
            : Number(reel.curtidas),

        comentarios:
          reel.comentarios === null ||
          reel.comentarios === undefined ||
          reel.comentarios === ""
            ? null
            : Number(reel.comentarios),

        origem_views: reel.origem_views || "card"
      };
    });

    // ================================
    // REMOVER DUPLICADOS
    // ================================

    const mapa = new Map();

    for (const reel of reels) {
      if (!reel.url) continue;

      mapa.set(reel.url, reel);
    }

    reels = Array.from(mapa.values());

    // ================================
    // ORDENAR
    // ================================

    reels.sort((a, b) => {
      const ordemA = Number(a.ordem) || 999999;
      const ordemB = Number(b.ordem) || 999999;

      return ordemA - ordemB;
    });

    // Recriar ordem sequencial
    reels = reels.map((reel, index) => ({
      ...reel,
      ordem: index + 1
    }));

    // ================================
    // DATA ATUAL
    // ================================

    const atualizadoEm = new Date().toISOString();

    // ================================
    // GERAR JSON
    // ================================

    const jsonData = {
      perfil: perfilLimpo,
      atualizado_em: atualizadoEm,
      total: reels.length,
      reels: reels
    };

    const jsonContent = JSON.stringify(jsonData, null, 2);

    // ================================
    // GERAR CSV
    // ================================

    const csvHeader =
      "ordem,data,hora,dia,views,curtidas,comentarios,url,origem_views";

    const csvRows = reels.map((reel) => {
      return [
        reel.ordem,
        csvEscape(reel.data),
        csvEscape(reel.hora),
        csvEscape(reel.dia),
        reel.views ?? "",
        reel.curtidas ?? "",
        reel.comentarios ?? "",
        csvEscape(reel.url),
        csvEscape(reel.origem_views)
      ].join(",");
    });

    const csvContent = [
      csvHeader,
      ...csvRows
    ].join("\n");

    // ================================
    // NOMES DOS ARQUIVOS
    // ================================

    const jsonFile = `${perfilLimpo}_reels.json`;
    const csvFile = `${perfilLimpo}_reels.csv`;

    // ================================
    // SALVAR JSON
    // ================================

    await salvarArquivoGitHub(
      jsonFile,
      jsonContent,
      `Atualizar ${jsonFile}`,
      GITHUB_TOKEN,
      GITHUB_OWNER,
      GITHUB_REPO,
      GITHUB_BRANCH
    );

    // ================================
    // SALVAR CSV
    // ================================

    await salvarArquivoGitHub(
      csvFile,
      csvContent,
      `Atualizar ${csvFile}`,
      GITHUB_TOKEN,
      GITHUB_OWNER,
      GITHUB_REPO,
      GITHUB_BRANCH
    );

    // ================================
    // ATUALIZAR CONFIG.JSON
    // ================================

    const config = await obterConfigGitHub(
      GITHUB_TOKEN,
      GITHUB_OWNER,
      GITHUB_REPO,
      GITHUB_BRANCH
    );

    let contas = [];

    if (config && Array.isArray(config.contas)) {
      contas = config.contas;
    }

    // Remover conta antiga
    contas = contas.filter(
      (conta) => conta.perfil !== perfilLimpo
    );

    // Adicionar conta atual
    contas.push({
      perfil: perfilLimpo,
      arquivo_json: jsonFile,
      arquivo_csv: csvFile
    });

    // Ordenar alfabeticamente
    contas.sort((a, b) =>
      a.perfil.localeCompare(b.perfil)
    );

    const novoConfig = {
      contas: contas
    };

    await salvarArquivoGitHub(
      "config.json",
      JSON.stringify(novoConfig, null, 2),
      "Atualizar config.json",
      GITHUB_TOKEN,
      GITHUB_OWNER,
      GITHUB_REPO,
      GITHUB_BRANCH
    );

    // ================================
    // RESPOSTA
    // ================================

    return res.status(200).json({
      ok: true,
      perfil: perfilLimpo,
      total: reels.length,
      json: jsonFile,
      csv: csvFile,
      config: "config.json",
      atualizado_em: atualizadoEm
    });

  } catch (error) {
    console.error("Erro na API:", error);

    return res.status(500).json({
      ok: false,
      erro: "Erro interno da API",
      detalhe: error.message
    });
  }
}


// ============================================================
// ESCAPAR CSV
// ============================================================

function csvEscape(valor) {
  if (valor === null || valor === undefined) {
    return "";
  }

  const texto = String(valor);

  if (
    texto.includes(",") ||
    texto.includes('"') ||
    texto.includes("\n") ||
    texto.includes("\r")
  ) {
    return `"${texto.replace(/"/g, '""')}"`;
  }

  return texto;
}


// ============================================================
// URL DA API DO GITHUB
// ============================================================

function githubUrl(owner, repo, path) {
  return `https://api.github.com/repos/${owner}/${repo}/contents/${encodeURIComponent(
    path
  )}`;
}


// ============================================================
// OBTER ARQUIVO DO GITHUB
// ============================================================

async function obterArquivoGitHub(
  path,
  token,
  owner,
  repo,
  branch
) {
  const url = githubUrl(owner, repo, path);

  const response = await fetch(
    `${url}?ref=${encodeURIComponent(branch)}`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
      }
    }
  );

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    const texto = await response.text();

    throw new Error(
      `Erro ao consultar ${path}: ${response.status} ${texto}`
    );
  }

  return await response.json();
}


// ============================================================
// SALVAR ARQUIVO NO GITHUB
// ============================================================

async function salvarArquivoGitHub(
  path,
  content,
  message,
  token,
  owner,
  repo,
  branch
) {
  const existente = await obterArquivoGitHub(
    path,
    token,
    owner,
    repo,
    branch
  );

  const encoded = Buffer.from(
    content,
    "utf8"
  ).toString("base64");

  const body = {
    message,
    content: encoded,
    branch
  };

  if (existente && existente.sha) {
    body.sha = existente.sha;
  }

  const url = githubUrl(owner, repo, path);

  const response = await fetch(url, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
      "X-GitHub-Api-Version": "2022-11-28"
    },
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    const texto = await response.text();

    throw new Error(
      `Erro ao salvar ${path}: ${response.status} ${texto}`
    );
  }

  return await response.json();
}


// ============================================================
// OBTER CONFIG.JSON
// ============================================================

async function obterConfigGitHub(
  token,
  owner,
  repo,
  branch
) {
  const arquivo = await obterArquivoGitHub(
    "config.json",
    token,
    owner,
    repo,
    branch
  );

  if (!arquivo || !arquivo.content) {
    return {
      contas: []
    };
  }

  const decoded = Buffer.from(
    arquivo.content.replace(/\n/g, ""),
    "base64"
  ).toString("utf8");

  try {
    return JSON.parse(decoded);
  } catch {
    return {
      contas: []
    };
  }
}
