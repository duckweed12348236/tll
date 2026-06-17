<template>
  <view class="address-page">
    <!-- 地址列表 -->
    <view v-if="addresses.length === 0" class="empty-items">
      <text class="empty-text">暂无地址</text>
    </view>
    <uni-swipe-action v-else>
      <uni-swipe-action-item
          v-for="(address) in addresses"
          :key="address.id"
          :right-options="address.isDefault ? partialOptions : options"
          auto-close
          :threshold="20"
          @click="async ({content}) => await handleAddress(address, content.key)">
        <view @click="() => chooseAddress(address)" class="address-item">
          <view class="address-header">
            <text class="name">{{ address.name }}</text>
            <text class="phone">{{ address.telephone }}</text>
            <view v-if="address.isDefault" class="default-tag">默认</view>
          </view>
          <view class="address-body">
            <text class="full-address">{{ address.region }} {{ address.detail }}</text>
          </view>
        </view>
      </uni-swipe-action-item>
    </uni-swipe-action>

    <!-- 添加地址按钮 -->
    <view class="add-btn-container">
      <button type="warn" class="add-btn" @click="() => goToEditAddress()">
        <uni-icons type="plus" size="20" color="#fff"/>
        <text>添加地址</text>
      </button>
    </view>
  </view>
</template>

<script setup>
import {ref} from "vue"
import {request} from "@/plugins/request"
import {onLoad, onUnload, onShow} from "@dcloudio/uni-app"
import {serializer} from "@/plugins/serializer"
import {useStore} from "@/plugins/stores"

const store = useStore()
const addresses = ref([])
const productId = ref(null)
const partialOptions = [
  {
    text: "编辑",
    style: {
      backgroundColor: "#42B983"
    },
    key: 2
  },
  {
    text: "删除",
    style: {
      backgroundColor: "#dd524d"
    },
    key: 3
  }
]
const options = [
  {
    text: "设为默认",
    style: {
      backgroundColor: "#007aff"
    },
    key: 1
  },
  ...partialOptions
]

const fetchAddresses = async () => {
  const response = await request.get("/user/address")
  if (response.code === 1) {
    addresses.value = response.data.map(address => ({
      ...address,
      isDefault: store.user.defaultAddressId === address.id
    }))
  } else {
    uni.showToast({
      title: response.message,
      icon: "error"
    })
  }
}

const deleteAddress = (address) => {
  uni.showModal({
    title: "确认删除",
    content: "确认删除该地址？",
    success: async ({confirm}) => {
      if (confirm) {
        const response = await request.delete("/user/address", address.id)
        if (response.code === 1) {
          addresses.value = addresses.value.filter((item) => item.id !== address.id)
          uni.showToast({
            title: "删除成功",
            icon: "success"
          })
        } else {
          uni.showToast({
            title: response.message,
            icon: "error"
          })
        }
      }
    }
  })
}

const goToEditAddress = (address = null) => {
  let url = "/pages/address-edit"
  if (address !== null) {
    url = `${url}?address=${encodeURIComponent(serializer.stringify(address))}`
  }
  uni.navigateTo({url: url})
}

const setDefaultAddress = async (address) => {
  uni.showLoading({title: "提交中"})
  const response = await request.post("/user/address", {}, address.id)

  if (response.code === 1) {
    uni.showToast({
      title: "设置成功",
      icon: "success"
    })
    for (const address of addresses.value) {
      if (address.isDefault) {
        address.isDefault = false
        break
      }
    }
    address.isDefault = true
    store.user = {
      ...store.user,
      defaultAddressId: address.id
    }
  } else {
    uni.showToast({
      title: response.message,
      icon: "error"
    })
  }
  uni.hideLoading()
}

const chooseAddress = (address) => {
  if (productId.value === null) {
    return
  }
  uni.$emit("chooseAddress", address)
  uni.navigateBack()
}

const handleAddress = async (address, key) => {
  switch (key) {
    case  1:
      await setDefaultAddress(address)
      break
    case 2:
      goToEditAddress(address)
      break
    case 3:
      deleteAddress(address)
      break
  }
}

onLoad((options) => {
  if (options.hasOwnProperty("productId")) {
    productId.value = serializer.parse(options.productId)
  }
})

onUnload(() => {
  uni.$off("chooseAddress")
})

onShow(async () => {
  await fetchAddresses()
})
</script>

<style scoped>
.address-page {
  min-height: 100vh;
  background-color: #f8f8f8;
  padding-bottom: 120rpx;
}

.empty-items {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 60vh;
}

.empty-text {
  font-size: 32rpx;
  color: #999;
}

.address-item {
  padding: 30rpx;
  background-color: #fff;
  border-bottom: 1rpx solid #eee;
}

.address-header {
  display: flex;
  align-items: center;
  margin-bottom: 20rpx;
}

.name {
  font-size: 32rpx;
  font-weight: 500;
  color: #333;
}

.phone {
  font-size: 28rpx;
  color: #666;
  margin-left: 30rpx;
}

.default-tag {
  margin-left: auto;
  background-color: #007aff;
  color: #fff;
  font-size: 24rpx;
  padding: 6rpx 16rpx;
  border-radius: 20rpx;
}

.address-body {
  display: flex;
  flex-direction: column;
}

.full-address {
  font-size: 28rpx;
  color: #333;
  line-height: 1.4;
}

.add-btn-container {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 20rpx 30rpx;
  background-color: #fff;
  box-shadow: 0 -2rpx 10rpx rgba(0, 0, 0, 0.05);
}

.add-btn {
  width: 100%;
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 44rpx;
  font-size: 32rpx;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10rpx;
}

.add-btn::after {
  border: none;
}

.add-btn text {
  color: #fff;
}
</style>