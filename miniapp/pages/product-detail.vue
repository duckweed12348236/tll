<template>
  <view class="product-detail">
    <!-- 封面轮播图 -->
    <swiper v-if="product.covers && product.covers.length" class="cover-swiper" :indicator-dots="true" :autoplay="false"
            :circular="true">
      <swiper-item v-for="(cover, index) in product.covers" :key="index" @tap="previewImage(product.covers, index)">
        <image class="cover-image" :src="cover" mode="aspectFill"/>
      </swiper-item>
    </swiper>
    <view v-else class="cover-placeholder">
      <view class="placeholder-image">暂无图片</view>
    </view>

    <!-- 商品基本信息 -->
    <view class="basic-info">
      <view class="name-price">
        <text class="price">¥{{ product.price }}</text>
        <text class="name">{{ product.name }}</text>
      </view>
      <view class="meta">
        <text class="limit" v-if="product.perMaxQuantity">限购{{ product.perMaxQuantity }}件</text>
      </view>
    </view>

    <!-- 商品详情图片（竖向展示） -->
    <view class="detail-section">
      <text class="section-title">商品详情</text>
      <view class="detail-images">
        <image
            v-for="(detail, idx) in product.details"
            :key="idx"
            class="detail-image"
            :src="detail"
            mode="widthFix"
            @tap="previewImage(product.details, idx)"
        />
      </view>
    </view>

    <!-- 底部操作栏 -->
    <view class="bottom-nav-wrapper">
      <uni-goods-nav
          :fill="true"
          :options="[]"
          :buttonGroup="actions"
          @buttonClick="() => popupInstance.open()"
      />
    </view>

    <!-- 下单弹窗 -->
    <uni-popup ref="popupInstance" type="bottom" background-color="#fff" class="order-popup">
      <view class="popup-content">
        <view class="popup-header">
          <text class="popup-title">确认订单</text>
          <uni-icons type="closeempty" size="24" color="#999" @tap="() => popupInstance.close()"/>
        </view>

        <!-- 商品信息 -->
        <view class="popup-product">
          <view class="product-cover-row">
            <image
                class="product-cover"
                :src="product.covers"
                mode="aspectFill"
            />
            <view class="product-info">
              <text class="product-name">{{ product.name }}</text>
              <text class="product-price">¥{{ product.price }}</text>
            </view>
          </view>
        </view>

        <!-- 数量选择 -->
        <view class="popup-row">
          <text class="row-label">购买数量</text>
          <view class="quantity-wrapper">
            <uni-number-box
                :min="1"
                :max="Math.max(1, product.perMaxQuantity || 999)"
                v-model="quantity"
            />
            <text v-if="product.perMaxQuantity" class="limit-hint">限购{{ product.perMaxQuantity }}件</text>
          </view>
        </view>

        <!-- 地址选择 -->
        <view class="popup-row address-row" @tap="chooseAddress">
          <text class="row-label">配送地址</text>
          <view class="address-info">
            <view v-if="address.id">
              <text class="address-text">{{ address.name }} {{ address.telephone }}</text>
              <text class="address-text">{{ address.region }} {{ address.detail }}</text>
            </view>
            <view v-else class="address-placeholder">
              <text class="placeholder-text">请选择收货地址</text>
            </view>
            <uni-icons type="right" size="16" color="#999"></uni-icons>
          </view>
        </view>

        <!-- 总金额 -->
        <view class="popup-row total-row">
          <text class="row-label">总金额</text>
          <text class="total-amount">¥{{ totalAmount.toFixed(2) }}</text>
        </view>

        <!-- 下单按钮 -->
        <view class="popup-footer">
          <button class="order-btn" @tap="placeOrder">立即下单</button>
        </view>
      </view>
    </uni-popup>
  </view>
</template>

<script setup>
import {computed, reactive, ref} from "vue"
import {onShow, onLoad, onUnload} from "@dcloudio/uni-app"
import {request} from "@/plugins/request"
import {serializer} from "@/plugins/serializer"

const quantity = ref(1)
const address = reactive({
  id: 0,
  name: "",
  telephone: "",
  region: "",
  detail: ""
})
const product = reactive({
  id: 0,
  name: "mao",
  price: 100,
  stock: 0,
  perMaxQuantity: 100,
  covers: ["/static/logo.png", "/static/logo.png"],
  details: ["/static/logo.png", "/static/logo.png"]
})
const popupInstance = ref(null)

// 总金额（保留两位小数，不四舍五入）
const totalAmount = computed(() => {
  const price = Number(product.price) || 0
  const total = price * quantity.value
  // 保留两位小数，不四舍五入（截断）
  return Math.floor(total * 100) / 100
})

const fetchProduct = async (productId) => {
  const response = await request.get("/shopping/product", {}, productId)
  if (response.code === 1) {
    Object.assign(product, response.data[0])
    Object.assign(address, response.data[1])
  } else {
    uni.showToast({
      title: response.message,
      icon: "error"
    })
  }
}

const placeOrder = async () => {
  uni.showLoading({
    title: "正在下单..."
  })
  const response = await request.post("/shopping/order", {
    productId: product.id,
    addressId: address.id,
    quantity: quantity.value
  })

  if (response.code === 1) {
    uni.showToast({
      title: "下单成功",
      icon: "success"
    })
    popupInstance.value.close()
  } else {
    uni.showToast({
      title: response.message,
      icon: "error"
    })
  }
  uni.hideLoading()
}

const actions = [{
  text: "立即抢购",
  backgroundColor: "linear-gradient(135deg, #FF6B6B, #FF8E53)",
  color: "#fff"
}]

const previewImage = (urls, current) => {
  uni.previewImage({
    urls: urls,
    current
  })
}

const chooseAddress = () => {
  uni.navigateTo({
    url: `/pages/address?discountedProductId=${product.id}`
  })
}
// 在onLoad生命周期函数中，可以接收到上个页面传来的参数
onLoad((options) => {
  // var EnvUtils = plus.android.importClass("com.alipay.sdk.app.EnvUtils")
  // EnvUtils.setEnv(EnvUtils.EnvEnum.SANDBOX)
  uni.$on("chooseAddress", (data) => Object.assign(address, data))

  if (options.hasOwnProperty("productId")) {
    product.id = serializer.parse(options.productId)
  }
})

onUnload(() => {
  uni.$off("chooseAddress")
})

onShow(async () => {
  await fetchProduct(product.id)
})
</script>

<style scoped lang="scss">
.product-detail {
  padding-bottom: 120rpx; // 给底部操作栏留出空间
  background-color: #f8f8f8;
  min-height: 100vh;
}

.cover-swiper {
  height: 375px;
  background-color: #fff;

  .cover-image {
    width: 100%;
    height: 100%;
  }
}

.basic-info {
  padding: 20rpx 30rpx;
  background-color: #fff;
  margin-bottom: 20rpx;

  .name-price {
    display: block;
    margin-bottom: 20rpx;

    .price {
      font-size: 44rpx;
      color: #ff6b6b;
      font-weight: bold;
      display: block;
      margin-bottom: 10rpx;
    }

    .name {
      font-size: 36rpx;
      font-weight: bold;
      color: #333;
      display: block;
      line-height: 1.4;
    }
  }

  .meta {
    display: flex;
    justify-content: space-between;
    font-size: 28rpx;
    color: #666;

    .limit {
      color: #ff8e53;
    }
  }
}

.detail-section {
  background-color: #fff;
  padding: 30rpx;
  margin-bottom: 20rpx;

  .section-title {
    display: block;
    font-size: 32rpx;
    font-weight: bold;
    color: #333;
    margin-bottom: 30rpx;
  }

  .detail-images {
    .detail-image {
      width: 100%;
      margin-bottom: 20rpx;
      border-radius: 10rpx;
    }
  }
}

.cover-placeholder {
  height: 375px;
  background-color: #f0f0f0;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #999;
  font-size: 32rpx;
}

.placeholder-image {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

/* 底部操作栏固定定位 */
.bottom-nav-wrapper {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 999;
}

/* 弹窗样式 - 确保层级高于底部操作栏 */
.order-popup {
  z-index: 1000 !important;
}

.popup-content {
  padding: 40rpx 30rpx;
  border-radius: 30rpx 30rpx 0 0;
  background-color: #fff;
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 40rpx;
  padding-bottom: 20rpx;
  border-bottom: 1rpx solid #f0f0f0;
}

.popup-title {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
}

.popup-product {
  margin-bottom: 40rpx;

  .product-cover-row {
    display: flex;
    align-items: center;

    .product-cover {
      width: 120rpx;
      height: 120rpx;
      border-radius: 10rpx;
      margin-right: 30rpx;
      flex-shrink: 0;
    }

    .product-info {
      flex: 1;

      .product-name {
        display: block;
        font-size: 32rpx;
        color: #333;
        margin-bottom: 10rpx;
        line-height: 1.4;
      }

      .product-price {
        font-size: 36rpx;
        color: #ff6b6b;
        font-weight: bold;
      }
    }
  }
}

.popup-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 30rpx 0;
  border-bottom: 1rpx solid #f0f0f0;

  .row-label {
    font-size: 32rpx;
    color: #333;
  }

  .quantity-wrapper {
    display: flex;
    flex-direction: column;
    align-items: flex-end;

    .limit-hint {
      margin-top: 10rpx;
      font-size: 24rpx;
      color: #ff8e53;
    }
  }
}

.address-row {
  .address-info {
    flex: 1;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-left: 30rpx;

    .address-text {
      display: block;
      font-size: 28rpx;
      color: #666;
      line-height: 1.5;
    }

    .address-placeholder {
      .placeholder-text {
        font-size: 28rpx;
        color: #999;
      }
    }
  }
}

.total-row {
  border-bottom: none;

  .total-amount {
    font-size: 44rpx;
    color: #ff6b6b;
    font-weight: bold;
  }
}

.popup-footer {
  margin-top: 40rpx;

  .order-btn {
    width: 100%;
    height: 90rpx;
    line-height: 90rpx;
    background: linear-gradient(135deg, #FF6B6B, #FF8E53);
    color: #fff;
    font-size: 32rpx;
    border-radius: 45rpx;
    border: none;

    &:after {
      border: none;
    }
  }
}
</style>