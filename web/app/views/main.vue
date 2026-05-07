<script setup>
import {router, routes} from "@/plugins/router.js"
import {UserOutlined} from "@ant-design/icons-vue"
import {ref} from "vue"

const currentRoute = ref(router.currentRoute.value.name)
const menuOptions = routes[0].children.map(route => ({
  label: route.meta.label,
  key: route.name,
  icon: route.meta.icon
}))
const userOptions = [
  {label: "个人中心", key: "profile"},
  {label: "退出登录", key: "logout"}
]

const navigate = async (key) => {
  currentRoute.value = key
  await router.push({name: key})
}

const handleLogout = (key) => {
  if (key === "logout") {
    // 退出登录逻辑
    console.log("logout")
    // 实际开发中调用退出接口，清除token等
  } else if (key === "profile") {
    // 跳转到个人中心
    console.log("profile")
  }
}
</script>

<template>
  <n-message-provider>
    <n-dialog-provider>
      <n-layout has-sider class="h-screen">
        <!-- 侧边栏 -->
        <n-layout-sider collapse-mode="width" width="20vh" bordered show-trigger>
          <n-menu
              v-model:value="currentRoute"
              :options="menuOptions"
              :on-update:value="navigate"
              mode="vertical"/>
        </n-layout-sider>

        <n-layout>
          <!-- 顶部栏 -->
          <n-layout-header bordered class="h-16 px-6 flex items-center justify-between">
            <div class="flex items-center gap-4">
              <n-dropdown :options="userOptions" @select="(key) => handleLogout(key)">
                <n-button quaternary>
                  <template #icon>
                    <UserOutlined/>
                  </template>
                  管理员
                </n-button>
              </n-dropdown>
            </div>
          </n-layout-header>

          <!-- 内容区域 -->
          <n-layout-content class="p-6 bg-gray-50">
            <router-view/>
          </n-layout-content>
        </n-layout>
      </n-layout>
    </n-dialog-provider>
  </n-message-provider>
</template>

<style scoped>
.n-layout-sider {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
</style>