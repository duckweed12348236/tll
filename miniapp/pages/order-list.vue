<template>
  <view class="page-container">
    <!-- 订单状态筛选 -->
    <view class="filter-container">
      <uni-segmented-control
          :values="filterOptions"
          @clickItem="async ({currentIndex}) => await fetchOrders(currentIndex - 1)"
          style-type="text"
          active-color="#ce4031"/>
    </view>

    <!-- 订单列表 -->
    <view class="order-list" v-if="orders.length > 0">
      <view
          class="order-card"
          v-for="order in orders"
          :key="order.id"
          @click="viewOrder(order)">
        <view class="order-header">
          <text class="order-id">订单号: {{ order.id }}</text>
          <view class="order-status" :class="statusOptions[order.status].className">
            {{ statusOptions[order.status].label }}
          </view>
        </view>

        <view class="order-body">
          <image
              class="product-cover"
              :src="order.product.covers[0]"
              mode="aspectFill"
          />
          <view class="order-info">
            <text class="product-name">{{ order.product.name }}</text>
            <view class="order-details">
              <text class="detail-item">数量: {{ order.quantity }}</text>
              <text class="detail-item">金额: ￥{{ order.amount }}</text>
              <text class="detail-item">下单时间: {{ formatTime(order.creationTime) }}</text>
            </view>
          </view>
        </view>

        <view class="order-footer">
          <view class="footer-left">
            <text class="total-amount">实付: ￥{{ order.amount }}</text>
          </view>
          <view class="footer-right">
            <button class="btn" @click.stop="deleteOrder(order)" type="warn">删除订单</button>
          </view>
        </view>
      </view>
    </view>

    <!-- 空状态 -->
    <view class="empty-container" v-else>
      <text class="empty-text">暂无订单</text>
    </view>
  </view>
</template>

<script setup>
import {ref} from "vue"
import {request} from "@/plugins/request"
import {onShow} from "@dcloudio/uni-app"

const orders = ref([
  {
    id: 1,
    status: 2,
    quantity: 1,
    amount: 100,
    creationTime: 1645600000000,
    product: {
      id: 1,
      name: "商品1",
      price: 100,
      covers: ["/static/logo.png"]
    }
  }
])
const filterOptions = ["全部", "未支付", "已支付", "配送中", "已完成", "退款中", "已退款"]
const statusOptions = {
  0: {label: "未支付", className: "status-unpaid"},
  1: {label: "已支付", className: "status-paid"},
  2: {label: "配送中", className: "status-delivering"},
  3: {label: "已完成", className: "status-completed"},
  4: {label: "退款中", className: "status-refunding"},
  5: {label: "已退款", className: "status-refunded"}
}

const formatTime = (timestamp) => {
  if (!timestamp) return ""
  const date = new Date(timestamp)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  const hour = String(date.getHours()).padStart(2, "0")
  const minute = String(date.getMinutes()).padStart(2, "0")
  return `${year}-${month}-${day} ${hour}:${minute}`
}

const fetchOrders = async (option = -1) => {
  const response = await request.get("/shopping/order", {option})
  if (response.code === 1) {
    orders.value = response.data
  } else {
    uni.showToast({
      title: response.message,
      icon: "error"
    })
  }
}

const deleteOrder = (order) => {
  uni.showModal({
    title: "提示",
    content: "确定要删除该订单吗？",
    success: async ({confirm}) => {
      if (confirm) {
        const response = await request.delete("/shopping/order", order.id)

        if (response.code === 1) {
          await fetchOrders()
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

const viewOrder = (order) => {
  uni.navigateTo({
    url: `/pages/order-detail?order=${encodeURIComponent(JSON.stringify(order))}`
  })
}

onShow(async () => {
  await fetchOrders()
})
</script>

<style scoped lang="scss">
.page-container {
  background-color: #f5f5f5;
  min-height: 100vh;
  padding: 20rpx;
}

.filter-container {
  padding: 20rpx;
  margin-bottom: 20rpx;
}

.order-list {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.order-card {
  background: #ffffff;
  border-radius: 16rpx;
  overflow: hidden;
  box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.06);
  padding: 30rpx;
}

.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20rpx;
  padding-bottom: 20rpx;
  border-bottom: 1rpx solid #f0f0f0;
}

.order-id {
  font-size: 26rpx;
  color: #666;
}

.order-status {
  font-size: 24rpx;
  padding: 6rpx 16rpx;
  border-radius: 20rpx;
}

.status-unpaid {
  background-color: #ffeaea;
  color: #ff4444;
}

.status-paid {
  background-color: #e8f5e8;
  color: #28a745;
}

.status-delivering {
  background-color: #e8f0fe;
  color: #007bff;
}

.status-completed {
  background-color: #f0f0f0;
  color: #666;
}

.status-refunding {
  background-color: #fff3cd;
  color: #ffc107;
}

.status-refunded {
  background-color: #f8f9fa;
  color: #6c757d;
}

.order-body {
  display: flex;
  gap: 20rpx;
  margin-bottom: 20rpx;
}

.product-cover {
  width: 160rpx;
  height: 160rpx;
  border-radius: 12rpx;
  flex-shrink: 0;
}

.order-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.product-name {
  font-size: 30rpx;
  color: #333;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 10rpx;
}

.order-details {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.detail-item {
  font-size: 24rpx;
  color: #999;
}

.order-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 20rpx;
  border-top: 1rpx solid #f0f0f0;
}

.total-amount {
  font-size: 28rpx;
  color: #ff4444;
  font-weight: bold;
}

.btn {
  font-size: 24rpx;
  border: none;
  outline: none;
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