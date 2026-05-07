<template>
  <view class="address-edit">
    <uni-forms ref="form" :model="address" :rules="rules">
      <uni-forms-item label="收货人姓名" name="name" required>
        <view class="input-container">
          <input
              v-model="address.name"
              type="text"
              placeholder="请输入收货人姓名"
              placeholder-style="color: #999; font-size: 30rpx;"
              class="input-field"/>
          <uni-icons
              v-if="address.name"
              type="clear"
              size="20"
              color="#ccc"
              @click="() => address.name = ''"
              class="clear-icon"
          />
        </view>
      </uni-forms-item>
      <uni-forms-item label="手机号码" name="telephone" required>
        <view class="input-container">
          <input
              v-model="address.telephone"
              type="number"
              maxlength="11"
              placeholder="请输入手机号"
              placeholder-style="color: #999; font-size: 30rpx;"
              class="input-field"/>
          <uni-icons
              v-if="address.telephone"
              type="clear"
              size="20"
              color="#ccc"
              @click="() => address.telephone = ''"
              class="clear-icon"
          />
        </view>
      </uni-forms-item>
      <uni-forms-item label="所在地区" name="region" required>
        <picker
            mode="multiSelector"
            :range="regionColumns"
            :value="regionIndexes"
            @change="chooseRegion"
            @columnchange="slideRegionColumn">
          <view class="picker-container">
            <text class="picker-text" :class="{ placeholder: !address.region }">
              {{ address.region || "请选择省/市/区" }}
            </text>
            <view class="picker-icons">
              <uni-icons
                  v-if="address.region"
                  type="clear"
                  size="20"
                  color="#ccc"
                  @click.stop="clearRegion"
                  class="clear-icon"/>
            </view>
          </view>
        </picker>
      </uni-forms-item>
      <uni-forms-item label="详细地址" name="detail" required>
        <view class="input-container">
          <input
              v-model="address.detail"
              type="text"
              placeholder="请输入详细地址（如街道、门牌号）"
              placeholder-style="color: #999; font-size: 30rpx;"
              class="input-field"/>
          <uni-icons
              v-if="address.detail"
              type="clear"
              size="20"
              color="#ccc"
              @click="() => address.detail = ''"
              class="clear-icon"/>
        </view>
      </uni-forms-item>
    </uni-forms>
    <view class="submit-btn">
      <button type="warn" @click="submit">保存地址</button>
    </view>
  </view>
</template>

<script setup>
import {reactive, ref, computed, onMounted} from "vue"
import {onLoad} from "@dcloudio/uni-app"
import {request} from "@/plugins/request"
import regions from "@/plugins/regions.js"
import {serializer} from "@/plugins/serializer"

const form = ref()
const address = reactive({
  id: null,
  name: "",
  telephone: "",
  region: "",
  detail: ""
})
const region = reactive({
  provinceIndex: 0,
  cityIndex: 0,
  districtIndex: 0
})
const regionColumns = [
  regions.map(p => p.name),
  regions[region.provinceIndex]?.city?.map(c => c.name) || [],
  regions[region.provinceIndex]?.city?.[region.cityIndex]?.area || []
]
const regionIndexes = computed(() => [region.provinceIndex, region.cityIndex, region.districtIndex])
const rules = {
  name: {
    rules: [
      {required: true, errorMessage: "请输入收货人姓名"}
    ]
  },
  telephone: {
    rules: [
      {required: true, errorMessage: "请输入手机号"},
      {pattern: /^1[3-9]\d{9}$/, errorMessage: "请输入正确的手机号"}
    ]
  },
  region: {
    rules: [
      {required: true, errorMessage: "请选择所在地区"}
    ]
  },
  detail: {
    rules: [
      {required: true, errorMessage: "请输入详细地址"}
    ]
  }
}

const chooseRegion = (event) => {
  const [provIdx, cityIdx, distIdx] = event.detail.value
  region.provinceIndex = provIdx
  region.cityIndex = cityIdx
  region.districtIndex = distIdx

  const province = regions[provIdx]?.name || ""
  const city = regions[provIdx]?.city?.[cityIdx]?.name || ""
  const district = regions[provIdx]?.city?.[cityIdx]?.area?.[distIdx] || ""

  address.region = `${province} ${city} ${district}`.trim()
}

const slideRegionColumn = (event) => {
  const {column, value} = event.detail
  if (column === 0) {
    region.provinceIndex = value
    region.cityIndex = 0
    region.districtIndex = 0
  } else if (column === 1) {
    region.cityIndex = value
    region.districtIndex = 0
  } else if (column === 2) {
    region.districtIndex = value
  }
}

const clearRegion = () => {
  address.region = ""
  Object.assign(region, {
    provinceIndex: 0,
    cityIndex: 0,
    districtIndex: 0
  })
}

const createAddress = async () => {
  const response = await request.post("/user/address", {
    name: address.name,
    telephone: address.telephone,
    region: address.region,
    detail: address.detail
  })

  if (response.code === 0) {
    uni.showToast({
      title: response.message,
      icon: "error"
    })
    throw new Error()
  }
}

const updateAddress = async () => {
  const response = await request.put("/user/address", {
    name: address.name,
    telephone: address.telephone,
    region: address.region,
    detail: address.detail
  }, address.id)

  if (response.code === 0) {
    uni.showToast({
      title: response.message,
      icon: "error"
    })
    throw new Error()
  }
}

const submit = async () => {
  uni.showLoading({
    title: "提交中"
  })
  try {
    await form.value.validate()
    if (address.id === null) {
      await createAddress()
    } else {
      await updateAddress()
    }
    uni.showToast({
      title: "保存成功",
      icon: "success"
    })
    setTimeout(() => {
      uni.navigateBack()
    }, 1500)
  } finally {
    uni.hideLoading()
  }
}

onLoad((options) => {
  if (options.hasOwnProperty("address")) {
    Object.assign(address, serializer.parse(decodeURIComponent(options.address)))
    uni.setNavigationBarTitle({title: "编辑地址"})

    if (address.region) {
      const parts = address.region.split(" ")
      if (parts.length >= 3) {
        const [prov, city, dist] = parts
        const provIdx = regions.findIndex(p => p.name === prov)
        if (provIdx >= 0) {
          region.provinceIndex = provIdx
          const cityIdx = regions[provIdx].city.findIndex(c => c.name === city)
          if (cityIdx >= 0) {
            region.cityIndex = cityIdx
            const distIdx = regions[provIdx].city[cityIdx].area.findIndex(d => d === dist)
            if (distIdx >= 0) {
              region.districtIndex = distIdx
            }
          }
        }
      }
    }
  }
})
</script>

<style scoped>
.address-edit {
  padding: 30rpx;
  background-color: #f8f8f8;
  min-height: 100vh;
}

.uni-forms {
  background-color: #fff;
  border-radius: 16rpx;
  padding: 0 30rpx;
  margin-bottom: 40rpx;
}

.uni-forms-item {
  padding: 30rpx 0;
  border-bottom: 1rpx solid #eee;
}

.uni-forms-item:last-child {
  border-bottom: none;
}

.uni-forms-item__label {
  font-size: 32rpx;
  color: #333;
  font-weight: 500;
  margin-bottom: 20rpx;
  display: block;
}

input {
  width: 100%;
  height: 80rpx;
  font-size: 30rpx;
  color: #333;
  background-color: transparent;
}

.input-container {
  display: flex;
  align-items: center;
  position: relative;
}

.input-field {
  flex: 1;
  height: 80rpx;
  font-size: 30rpx;
  color: #333;
  background-color: transparent;
}

.clear-icon {
  margin-left: 20rpx;
  flex-shrink: 0;
}

.picker-container {
  width: 100%;
  height: 80rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.picker-icons {
  display: flex;
  align-items: center;
  gap: 20rpx;
}

.picker-text {
  flex: 1;
  font-size: 30rpx;
  color: #333;
}

.picker-text.placeholder {
  color: #999;
}

.submit-btn {
  margin-top: 60rpx;
  padding: 0 30rpx;
}

.submit-btn button {
  width: 100%;
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 44rpx;
  font-size: 32rpx;
  color: #fff;
}

.submit-btn button:after {
  border: none;
}
</style>