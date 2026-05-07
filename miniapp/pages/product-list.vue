<template>
  <view class="page-container">
    <!-- 搜索栏 -->
    <view class="search-bar-container">
      <uni-search-bar
          v-model="keyword"
          placeholder="搜索商品"
          @confirm="handleSearch"
          @clear="handleClear"
          cancel-button="none"
          bg-color="#ffffff"
          radius="100"
      />
    </view>

    <!-- 商品宫格列表 -->
    <view class="product-grid-container" v-if="products.length > 0">
      <view class="product-grid">
        <view
            class="product-item"
            v-for="product in products"
            :key="product.id"
            @click="() => viewProduct(product)">
          <image
              class="product-cover"
              :src="product.covers && product.covers.length > 0 ? product.covers[0] : '/static/logo.png'"
              mode="aspectFill"
          />
          <view class="product-info">
            <text class="product-name">{{ product.name }}</text>
            <view class="product-price">
              <text class="price-symbol">￥</text>
              <text class="price-number">{{ product.price }}</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- 空状态 -->
    <view class="empty-container" v-else>
      <uni-icons type="document-empty" size="80" color="#ccc"/>
      <text class="empty-text">暂无商品</text>
    </view>
  </view>
</template>

<script setup>
import {ref} from "vue"
import {request} from "@/plugins/request"
import {onShow} from "@dcloudio/uni-app"

const products = ref([
    {
        id: 1,
        name: "商品1",
        price: 100,
        covers: ["/static/logo.png"]
    },
    {
        id: 2,
        name: "商品2",
        price: 200,
        covers: ["/static/logo.png"]
    }
])
const keyword = ref("")

const fetchProducts = async () => {
  let params = {}
  if (keyword.value) {
    params.keyword = keyword.value
  }
  const response = await request.get("/shopping/product", params)

  if (response.code === 1) {
    // products.value = response.data
  } else {
    uni.showToast({
      title: response.message,
      icon: "error"
    })
  }
}

const handleSearch = () => {
  fetchProducts()
}

const handleClear = () => {
  keyword.value = ""
  fetchProducts()
}

const viewProduct = (product) => {
  uni.navigateTo({
    url: `/pages/product-detail?productId=${product.id}`
  })
}

onShow(async () => {
  await fetchProducts()
})
</script>

<style scoped lang="scss">
.page-container {
  background-color: #f5f5f5;
  min-height: 100vh;
  padding: 20rpx;
}

.search-bar-container {
  margin-bottom: 30rpx;
}

.product-grid-container {
  margin-top: 20rpx;
}

.product-grid {
  display: flex;
  flex-wrap: wrap;
  margin: -10rpx;
}

.product-item {
  background: #ffffff;
  border-radius: 16rpx;
  overflow: hidden;
  box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.06);
  margin: 10rpx;
  width: calc(50% - 20rpx);
  display: flex;
  flex-direction: column;
}

.product-cover {
  width: 100%;
  height: 300rpx;
}

.product-info {
  padding: 20rpx;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.product-name {
  font-size: 28rpx;
  color: #333;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 10rpx;
  flex: 1;
}

.product-price {
  display: flex;
  align-items: baseline;
}

.price-symbol {
  font-size: 24rpx;
  color: #ff6b6b;
  font-weight: 500;
}

.price-number {
  font-size: 32rpx;
  color: #ff6b6b;
  font-weight: bold;
  margin-left: 4rpx;
}

.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding-top: 200rpx;
}

.empty-text {
  font-size: 28rpx;
  color: #999;
  margin-top: 20rpx;
}
</style>