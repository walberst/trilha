<script setup>
defineProps({
  faixa: {
    type: String,
    required: true,
  },
});

const rotulos = {
  baixo: "Baixo risco",
  medio: "Medio risco",
  alto: "Alto risco",
};
</script>

<template>
  <span class="badge-risco" :class="faixa">{{ rotulos[faixa] ?? faixa }}</span>
</template>
