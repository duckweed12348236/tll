<template>
  <div class="user-info">
    <div class="avatar-container">
      <img v-if="user.avatar" :src="user.avatar" alt="用户头像" class="avatar">
      <div v-else class="avatar-placeholder">
        <uni-icons type="person" size="40" color="#fff"/>
      </div>
    </div>
    <div class="username">{{ user.username }}</div>
  </div>

  <uni-list>
    <uni-list-item showArrow title="修改个人资料" to="/pages/user-detail"/>
    <uni-list-item showArrow title="我的地址" to="/pages/address-list"/>
    <uni-list-item showArrow title="我的订单" clickable @click="() => uni.switchTab({url: '/pages/order-list'})"/>
  </uni-list>

  <button type="warn" class="exit-button" @click="exit">退出登录</button>
</template>

<script setup>
import {useStore} from "@/plugins/stores"

const store = useStore()
const user = store.user

const exit = async () => {
  uni.showModal({
    title: "提示",
    content: "确定要退出登录吗？",
    success: async ({confirm}) => {
      if (confirm) {
        store.clear()
        uni.redirectTo({
          url: "/pages/login"
        })
      }
    }
  })
}
</script>

<style>
.user-info {
  display: flex;
  align-items: center;
  padding: 40rpx;
  background: linear-gradient(135deg, rgb(206, 64, 49) 0%, rgb(230, 67, 64) 100%);
  color: #fff;
}

.avatar-container {
  position: relative;
  margin-right: 20rpx;
}

.avatar {
  width: 130rpx;
  height: 130rpx;
  border-radius: 50%;
  border: 3rpx solid rgba(255, 255, 255, 0.3);
}

.avatar-placeholder {
  width: 130rpx;
  height: 130rpx;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 3rpx solid rgba(255, 255, 255, 0.3);
}

.username {
  font-size: 35rpx;
  font-weight: bold;
  margin-top: 5rpx;
}

.exit-button {
  margin-top: 40rpx;
  margin-left: 20rpx;
  margin-right: 20rpx;
  border-radius: 44rpx;
}
</style>