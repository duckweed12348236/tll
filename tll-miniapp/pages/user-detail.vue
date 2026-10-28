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
            :src="store.user.avatar"
            mode="widthFix">
        </image>
      </template>
    </uni-list-item>
    <uni-list-item
        @tap="() => dialog.open()"
        showArrow
        title="用户名"
        :rightText="store.user.username"
        link/>
  </uni-list>

  <uni-popup ref="dialog" type="dialog">
    <uni-popup-dialog
        mode="input"
        title="修改用户名"
        placeholder="请输入用户名"
        :model-value="store.user.username"
        @confirm="updateUsername"/>
  </uni-popup>
</template>

<script setup>
import {ref} from "vue"
import {useStore} from "@/plugins/stores"
import {SERVER_URL} from "@/config"
import {serializer} from "@/plugins/serializer"
import {request} from "@/plugins/request"

const store = useStore()
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
        url: `${SERVER_URL}/user/avatar`,
        header: {
          Authorization: `Bearer ${store.accessToken}`
        },
        filePath: images.tempFilePaths[0],
        name: "avatar",
        success: (response) => {
          const data = serializer.parse(response.data)
          store.user = {
            ...store.user,
            avatar: data.url.replace(/\\/g, "/")
          }
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
  const response = await request.post("/user/username", {value: username})
  if (response.code === 1) {
    store.user = {
      ...store.user,
      username: username
    }
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