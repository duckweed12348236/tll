<template>
  <view class="login-container">
    <view class="logo-container">
      <image class="logo-image" src="/static/logo.png"/>
    </view>

    <view class="form-container">
      <view class="input-row">
        <input type="text" placeholder="请输入手机号码" v-model="telephone">
      </view>
      <view class="input-row input-row-flex">
        <input class="input-field" type="text" placeholder="请输入验证码" v-model="code">
        <button type="warn" size="mini" @click="sendVerificationCode" v-if="!started">获取验证码</button>
        <button type="warn" size="mini" v-else>
          <uni-countdown
              :second="60"
              :show-day="false"
              :show-hour="false"
              :show-minute="false"
              @timeup="() => started = false"
              color="white"/>
        </button>
      </view>
    </view>

    <view class="button-container">
      <button type="warn" @click="login">登录</button>
    </view>
  </view>
</template>

<script setup>
import {ref} from "vue"
import {useStore} from "@/plugins/stores"
import {request} from "@/plugins/request"

const store = useStore()
const started = ref(false)
const telephone = ref("")
const code = ref("")
const telephoneRegex = /^1[3,4,5,6,7,8,9][0-9]{9}$/
const codeRegex = /[0-9]{4}/

const verifyTelephone = () => {
  if (!telephoneRegex.test(telephone.value)) {
    uni.showModal({
      title: "提示",
      content: "请输入正确格式的手机号"
    })
    return false
  }
  return true
}

const sendVerificationCode = async () => {
  if (!verifyTelephone()) {
    return
  }
  started.value = true

  const response = await request.get("/user/verification-code", {telephone: telephone.value})
  if (response.code === 0) {
    uni.showToast({
      title: response.message,
      icon: "error"
    })
  }
}

const login = async () => {
  if (!verifyTelephone()) {
    return
  }

  if (!codeRegex.test(code.value)) {
    uni.showModal({
      title: "提示",
      content: "请输入正确格式的验证码"
    })
    return
  }

  const response = await request.post("/user/login", {
    telephone: telephone.value,
    code: code.value
  })
  if (response.code === 1) {
    const {user, refreshToken, accessToken} = response.data
    store.user = {
      ...user,
      avatar: user.avatar.replace(/\\/g, "/")
    }
    store.refreshToken = refreshToken
    store.accessToken = accessToken
    uni.switchTab({
      url: "/pages/product-list"
    })
  } else {
    uni.showToast({
      title: response.message,
      icon: "error"
    })
  }
}
</script>

<style>
page {
  background-color: #fff;
}

.login-container {
  margin-top: 40rpx;
  padding: 20rpx;
}

.logo-container {
  text-align: center;
}

.logo-image {
  width: 140rpx;
  height: 140rpx;
}

.form-container {
  margin-top: 40rpx;
}

.input-row {
  padding: 20rpx;
  border-bottom-width: 1rpx;
  border-bottom-style: solid;
  border-bottom-color: var(--borderColor);
}

.input-row-flex {
  display: flex;
  flex-direction: row;
  align-items: center;
}

.input-field {
  flex: 1;
}

.button-container {
  margin-top: 40rpx;
}
</style>
