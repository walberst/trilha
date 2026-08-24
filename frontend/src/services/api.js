const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function requisitar(caminho, opcoes = {}) {
  const resposta = await fetch(`${BASE_URL}${caminho}`, {
    headers: { "Content-Type": "application/json" },
    ...opcoes,
  });
  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => ({}));
    throw new Error(corpo.detalhe || `Erro ${resposta.status} ao chamar ${caminho}`);
  }
  if (resposta.status === 204) return null;
  return resposta.json();
}

export function listarTurmas() {
  return requisitar("/turmas");
}

export function obterTurma(turmaId) {
  return requisitar(`/turmas/${turmaId}`);
}

export function listarAlunosPorRisco(
  turmaId,
  { pagina = 1, tamanhoPagina = 20, ordenarPor = "risco", direcao = "desc" } = {},
) {
  const parametros = new URLSearchParams({
    pagina,
    tamanho_pagina: tamanhoPagina,
    ordenar_por: ordenarPor,
    direcao,
  });
  return requisitar(`/turmas/${turmaId}/alunos?${parametros}`);
}

export function obterDetalheAluno(matriculaId) {
  return requisitar(`/matriculas/${matriculaId}`);
}
