<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import ListaAlunos from "../components/ListaAlunos.vue";
import { listarAlunosPorRisco, obterTurma } from "../services/api";
import { conectarCanalRisco } from "../services/websocket";

const props = defineProps({
  turmaId: { type: String, required: true },
});

const turma = ref(null);
const pagina = ref(1);
const tamanhoPagina = 10;
const ordenarPor = ref("risco");
const direcao = ref("desc");
const resultado = ref({ itens: [], total: 0, total_paginas: 0 });
const carregando = ref(true);
const erro = ref("");
const conectadoTempoReal = ref(false);
const ultimosAlertas = ref([]);

let canal = null;

async function carregarPagina() {
  carregando.value = true;
  erro.value = "";
  try {
    resultado.value = await listarAlunosPorRisco(props.turmaId, {
      pagina: pagina.value,
      tamanhoPagina,
      ordenarPor: ordenarPor.value,
      direcao: direcao.value,
    });
  } catch (falha) {
    erro.value = falha.message;
  } finally {
    carregando.value = false;
  }
}

function ordenar({ ordenarPor: novaColuna, direcao: novaDirecao }) {
  ordenarPor.value = novaColuna;
  direcao.value = novaDirecao;
  pagina.value = 1;
}

function tratarAlerta(alerta) {
  ultimosAlertas.value = [alerta, ...ultimosAlertas.value].slice(0, 5);

  // Se o aluno que mudou de faixa estiver na pagina atual, atualiza a linha
  // na hora em vez de esperar o professor recarregar a pagina.
  const linha = resultado.value.itens.find((item) => item.matricula_id === alerta.matricula_id);
  if (linha) {
    linha.faixa_risco = alerta.faixa_nova;
    linha.score_risco = alerta.score_risco;
  }
}

onMounted(async () => {
  turma.value = await obterTurma(props.turmaId).catch(() => null);
  await carregarPagina();
  canal = conectarCanalRisco(props.turmaId, tratarAlerta);
  conectadoTempoReal.value = true;
});

onBeforeUnmount(() => {
  canal?.fechar();
});

watch([pagina, ordenarPor, direcao], carregarPagina);
watch(
  () => props.turmaId,
  () => {
    pagina.value = 1;
    carregarPagina();
  },
);
</script>

<template>
  <div>
    <div class="cabecalho">
      <div>
        <h1>{{ turma?.nome ?? `Turma ${turmaId}` }}</h1>
        <div class="status-tempo-real">
          <span class="ponto"></span>
          {{ conectadoTempoReal ? "Recebendo atualizacoes de risco em tempo real" : "Conectando..." }}
        </div>
      </div>
    </div>

    <div class="grid-metricas">
      <div class="metrica">
        <div class="rotulo">Alunos matriculados</div>
        <div class="valor">{{ resultado.total }}</div>
      </div>
      <div class="metrica">
        <div class="rotulo">Ultimos alertas</div>
        <div class="valor">{{ ultimosAlertas.length }}</div>
      </div>
    </div>

    <p v-if="erro" class="erro">{{ erro }}</p>

    <div class="cartao">
      <ListaAlunos
        :itens="resultado.itens"
        :turma-id="turmaId"
        :ordenar-por="ordenarPor"
        :direcao="direcao"
        @ordenar="ordenar"
      />
      <div class="paginacao">
        <button :disabled="pagina <= 1" @click="pagina--">Anterior</button>
        <span>Pagina {{ pagina }} de {{ resultado.total_paginas || 1 }}</span>
        <button :disabled="pagina >= resultado.total_paginas" @click="pagina++">Proxima</button>
      </div>
    </div>
  </div>
</template>
