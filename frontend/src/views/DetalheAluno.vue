<script setup>
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import BadgeRisco from "../components/BadgeRisco.vue";
import { obterDetalheAluno } from "../services/api";

const props = defineProps({
  turmaId: { type: String, required: true },
  matriculaId: { type: String, required: true },
});

const detalhe = ref(null);
const erro = ref("");

function formatarData(valorIso) {
  if (!valorIso) return "Nunca";
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "long", timeStyle: "short" }).format(new Date(valorIso));
}

onMounted(async () => {
  try {
    detalhe.value = await obterDetalheAluno(props.matriculaId);
  } catch (falha) {
    erro.value = falha.message;
  }
});
</script>

<template>
  <div>
    <RouterLink class="link-voltar" :to="{ name: 'painel-professor', params: { turmaId } }"
      >&larr; Voltar para a turma</RouterLink
    >

    <p v-if="erro" class="erro">{{ erro }}</p>

    <template v-if="detalhe">
      <div class="cabecalho">
        <h1>{{ detalhe.aluno.nome }}</h1>
        <BadgeRisco :faixa="detalhe.matricula.faixa_risco" />
      </div>
      <p>{{ detalhe.aluno.email }} - {{ detalhe.turma.nome }}</p>

      <div class="grid-metricas">
        <div class="metrica">
          <div class="rotulo">Score de risco</div>
          <div class="valor">{{ detalhe.matricula.score_risco.toFixed(1) }}</div>
        </div>
        <div class="metrica">
          <div class="rotulo">Dias sem atividade</div>
          <div class="valor">{{ detalhe.dias_sem_atividade ?? "N/D" }}</div>
        </div>
        <div class="metrica">
          <div class="rotulo">Pontuacao recencia</div>
          <div class="valor">{{ detalhe.pontuacao_recencia.toFixed(0) }}</div>
        </div>
        <div class="metrica">
          <div class="rotulo">Pontuacao frequencia</div>
          <div class="valor">{{ detalhe.pontuacao_frequencia.toFixed(0) }}</div>
        </div>
      </div>

      <div class="cartao">
        <p><strong>Ultimo evento:</strong> {{ detalhe.matricula.ultimo_evento_tipo ?? "Nenhum registrado" }}</p>
        <p><strong>Quando:</strong> {{ formatarData(detalhe.matricula.ultimo_evento_em) }}</p>
        <p><strong>Engajamento nos ultimos 14 dias:</strong> {{ detalhe.matricula.soma_pesos_14d.toFixed(1) }} pontos</p>
        <p><strong>Status da matricula:</strong> {{ detalhe.matricula.status }}</p>
      </div>
    </template>
  </div>
</template>
