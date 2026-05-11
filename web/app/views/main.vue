<script setup>
import {router, routes} from "@/plugins/router.js"
import {ref} from "vue"

const currentRoute = ref(router.currentRoute.value.name)
const menuOptions = routes[0].children.map(route => ({
  label: route.meta.label,
  key: route.name,
  icon: route.meta.icon
}))

const navigate = async (key) => {
  currentRoute.value = key
  await router.push({name: key})
}
</script>

<template>
  <n-layout has-sider class="h-screen overflow-hidden">
    <!-- 侧边栏 -->
    <n-layout-sider collapse-mode="width" width="25vh" bordered show-trigger>
      <n-menu
          v-model:value="currentRoute"
          :options="menuOptions"
          :on-update:value="navigate"
          mode="vertical"/>
    </n-layout-sider>

    <n-layout>
      <n-layout-content class="p-6 bg-gray-50">
        <router-view/>
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<style scoped>
.n-layout-sider {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
</style>