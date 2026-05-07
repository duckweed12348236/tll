<script setup>
import {zhCN} from "naive-ui"
</script>

<template>
  <n-config-provider :locale="zhCN">
    <router-view/>
  </n-config-provider>
</template>

<style scoped>
</style>
