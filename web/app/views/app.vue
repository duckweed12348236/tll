<script setup>
import {zhCN} from "naive-ui"
</script>

<template>
  <n-config-provider :locale="zhCN">
    <n-message-provider>
      <n-dialog-provider>
        <router-view/>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<style scoped>
</style>
