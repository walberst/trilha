<script setup>
import { RouterLink } from "vue-router";
import BadgeRisco from "./BadgeRisco.vue";

const props = defineProps({
  itens: { type: Array, required: true },
  turmaId: { type: [String, Number], required: true },
  ordenarPor: { type: String, required: true },
  direcao: { type: String, required: true },
});

const emit = defineEmits(["ordenar"]);

const colunas = [
  { chave: "nome", rotulo: "Aluno" },
  { chave: "risco", rotulo: "Risco" },
  { chave: "ultimo_evento", rotulo: "Ultima atividade" },
];

function alternarOrdenacao(chave) {
  if (props.ordenarPor === chave) {
    emit("ordenar", { ordenarPor: chave, direcao: props.direcao === "asc" ? "desc" : "asc" });
  } else {
    emit("ordenar", { ordenarPor: chave, direcao: "desc" });
  }
}

function formatarData(valorIso) {
  if (!valorIso) return "Nunca";
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(valorIso));
}
</script>

<template>
  <table>
    <thead>
      <tr>
        <th v-for="coluna in colunas" :key="coluna.chave" @click="alternarOrdenacao(coluna.chave)">
          {{ coluna.rotulo }}
          <span v-if="ordenarPor === coluna.chave">{{ direcao === "asc" ? "^" : "v" }}</span>
        </th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="aluno in itens" :key="aluno.matricula_id">
        <td>{{ aluno.nome }}</td>
        <td><BadgeRisco :faixa="aluno.faixa_risco" /></td>
        <td>{{ formatarData(aluno.ultimo_evento_em) }}</td>
        <td>
          <RouterLink :to="{ name: 'detalhe-aluno', params: { turmaId, matriculaId: aluno.matricula_id } }">
            Ver detalhe
          </RouterLink>
        </td>
      </tr>
      <tr v-if="itens.length === 0">
        <td colspan="4">Nenhum aluno matriculado nesta turma ainda.</td>
      </tr>
    </tbody>
  </table>
</template>
