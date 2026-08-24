import { createRouter, createWebHistory } from "vue-router";
import DetalheAluno from "../views/DetalheAluno.vue";
import PainelProfessor from "../views/PainelProfessor.vue";

const routes = [
  { path: "/", redirect: "/turmas/1" },
  {
    path: "/turmas/:turmaId",
    name: "painel-professor",
    component: PainelProfessor,
    props: true,
  },
  {
    path: "/turmas/:turmaId/alunos/:matriculaId",
    name: "detalhe-aluno",
    component: DetalheAluno,
    props: true,
  },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});
