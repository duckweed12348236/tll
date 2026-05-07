<template>
  <uni-list>
    <uni-list-item showArrow @tap="updateAvatar" link>
      <template v-slot:header>
        <view class="d-flex a-center">头像</view>
      </template>
      <template v-slot:footer>
        <image
            class="rounded"
            style="height: 80rpx; width: 80rpx;"
            :src="user.avatar"
            mode="widthFix">
        </image>
      </template>
    </uni-list-item>
    <uni-list-item
        @tap="() => dialog.open()"
        showArrow
        title="用户名"
        :rightText="user.username"
        link/>
  </uni-list>

  <uni-popup ref="dialog" type="dialog">
    <uni-popup-dialog
        mode="input"
        title="修改用户名"
        placeholder="请输入用户名"
        :model-value="user.username"
        @confirm="updateUsername"/>
  </uni-popup>
</template>

<script setup>
import {ref} from "vue"
import {store} from "@/plugins/stores"
import {SERVER_CONFIG} from "@/config"
import {serializer} from "@/plugins/serializer"
import {request} from "@/plugins/request"

const user = store.user
let dialog = ref()

const updateAvatar = () => {
  uni.chooseImage({
    count: 1,
    extension: ["jpg", "jpeg", "png", "webp"],
    success(images) {
      uni.showLoading({
        title: "上传中"
      })

      uni.uploadFile({
        url: `${SERVER_CONFIG.baseUrl}/user/avatar`,
        header: {
          Authorization: `Bearer ${store.accessToken.value}`
        },
        filePath: images.tempFilePaths[0],
        name: "avatar",
        success: (response) => {
          const data = serializer.parse(response.data)
          store.setUser({
            ...user.value,
            avatar: data.url
          })
          uni.hideLoading()
        },
        fail: (error) => {
          uni.hideLoading()
          uni.showToast({
            title: error.errMsg,
            icon: "error"
          })
        }
      })
    }
  })
}

const updateUsername = async (username) => {
  const response = await request.post("/user/username", username)
  if (response.code === 1) {
    store.setUser({
      ...user.value,
      username: username
    })
  } else {
    uni.showToast({
      icon: "error",
      title: response.message
    })
  }
}
</script>

<style>

</style>