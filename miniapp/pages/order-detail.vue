<template>
  <view class="page-container">
    <!-- 订单状态卡片 -->
    <view class="status-card">
      <view class="status-icon">
        <uni-icons :type="getStatusIcon(order.status)" size="60" :color="getStatusColor(order.status)"/>
      </view>
      <view class="status-info">
        <text class="status-text">{{ getStatusText(order.status) }}</text>
        <text class="order-id">订单号: {{ order.id }}</text>
      </view>
    </view>

    <!-- 收货地址卡片 -->
    <view class="card address-card">
      <view class="card-header">
        <uni-icons type="location" size="24" color="#ce4031"/>
        <text class="card-title">收货地址</text>
      </view>
      <view class="card-body">
        <view class="address-info">
          <view class="address-row">
            <text class="label">收货人:</text>
            <text class="value">{{ order.address.name }}</text>
          </view>
          <view class="address-row">
            <text class="label">联系电话:</text>
            <text class="value">{{ order.address.telephone }}</text>
          </view>
          <view class="address-row">
            <text class="label">地区信息:</text>
            <text class="value">{{ order.address.region }}</text>
          </view>
          <view class="address-row">
            <text class="label">详细地址:</text>
            <text class="value">{{ order.address.detail }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 商品信息卡片 -->
    <view class="card product-card">
      <view class="card-header">
        <uni-icons type="shop" size="24" color="#ce4031"/>
        <text class="card-title">商品信息</text>
      </view>
      <view class="card-body">
        <view class="product-row">
          <image
              class="product-cover"
              :src="order.product.covers && order.product.covers.length > 0 ? order.product.covers[0] : '/static/logo.png'"
              mode="aspectFill"
          />
          <view class="product-details">
            <text class="product-name">{{ order.product.name }}</text>
            <view class="product-meta">
              <text class="meta-item">价格: ￥{{ order.product.price }}</text>
              <text class="meta-item">数量: {{ order.quantity }}</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- 订单信息卡片 -->
    <view class="card order-info-card">
      <view class="card-header">
        <uni-icons type="list" size="24" color="#ce4031"/>
        <text class="card-title">订单信息</text>
      </view>
      <view class="card-body">
        <view class="info-row">
          <text class="label">订单编号:</text>
          <text class="value">{{ order.id }}</text>
        </view>
        <view class="info-row">
          <text class="label">订单状态:</text>
          <text class="value" :style="{ color: getStatusColor(order.status) }">{{ getStatusText(order.status) }}</text>
        </view>
        <view class="info-row">
          <text class="label">商品名称:</text>
          <text class="value">{{ order.product.name }}</text>
        </view>
        <view class="info-row">
          <text class="label">商品数量:</text>
          <text class="value">{{ order.quantity }}</text>
        </view>
        <view class="info-row">
          <text class="label">订单金额:</text>
          <text class="value price">￥{{ order.amount }}</text>
        </view>
        <view class="info-row">
          <text class="label">下单时间:</text>
          <text class="value">{{ formatTime(order.creationTime) }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import {ref} from "vue"
import {onLoad} from "@dcloudio/uni-app"

const order = ref({})

const getStatusText = (status) => {
  const map = {
    0: '未支付',
    1: '已支付',
    2: '配送中',
    3: '已完成',
    4: '退款中',
    5: '已退款'
  }
  return map[status] || '未知状态'
}

const getStatusColor = (status) => {
  const map = {
    0: '#ff4444', // 未支付 - 红色
    1: '#28a745', // 已支付 - 绿色
    2: '#007bff', // 配送中 - 蓝色
    3: '#666',    // 已完成 - 灰色
    4: '#ffc107', // 退款中 - 黄色
    5: '#6c757d'  // 已退款 - 深灰
  }
  return map[status] || '#999'
}

const getStatusIcon = (status) => {
  const map = {
    0: 'wallet',      // 未支付
    1: 'checkmark',   // 已支付
    2: 'paperplane',  // 配送中
    3: 'checkbox',    // 已完成
    4: 'refresh',     // 退款中
    5: 'undo'         // 已退款
  }
  return map[status] || 'help'
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  const second = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hour}:${minute}:${second}`
}

onLoad((options) => {
  if (options.order) {
    try {
      order.value = JSON.parse(decodeURIComponent(options.order))
    } catch (e) {
      console.error('解析订单数据失败', e)
      uni.showToast({
        title: '订单数据错误',
        icon: 'error'
      })
      setTimeout(() => {
        uni.navigateBack()
      }, 1500)
    }
  } else {
    uni.showToast({
      title: '缺少订单信息',
      icon: 'error'
    })
    setTimeout(() => {
      uni.navigateBack()
    }, 1500)
  }
})
</script>

<style scoped lang="scss">
.page-container {
  background-color: #f5f5f5;
  min-height: 100vh;
  padding: 20rpx;
}

.status-card {
  background: linear-gradient(135deg, #ce4031, #e65041);
  border-radius: 16rpx;
  padding: 40rpx 30rpx;
  display: flex;
  align-items: center;
  margin-bottom: 20rpx;
  color: white;
  box-shadow: 0 8rpx 24rpx rgba(206, 64, 49, 0.3);
}

.status-icon {
  margin-right: 30rpx;
}

.status-info {
  display: flex;
  flex-direction: column;
}

.status-text {
  font-size: 36rpx;
  font-weight: bold;
  margin-bottom: 10rpx;
}

.order-id {
  font-size: 24rpx;
  opacity: 0.9;
}

.card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 30rpx;
  margin-bottom: 20rpx;
  box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.06);
}

.card-header {
  display: flex;
  align-items: center;
  margin-bottom: 20rpx;
  padding-bottom: 20rpx;
  border-bottom: 1rpx solid #f0f0f0;
}

.card-title {
  font-size: 28rpx;
  color: #333;
  margin-left: 10rpx;
  font-weight: 500;
}

.address-info {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.address-row {
  display: flex;
}

.label {
  font-size: 26rpx;
  color: #666;
  width: 140rpx;
  flex-shrink: 0;
}

.value {
  font-size: 26rpx;
  color: #333;
  flex: 1;
}

.product-row {
  display: flex;
  gap: 20rpx;
}

.product-cover {
  width: 160rpx;
  height: 160rpx;
  border-radius: 12rpx;
  flex-shrink: 0;
}

.product-details {
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
}

.product-meta {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
  margin-top: 10rpx;
}

.meta-item {
  font-size: 24rpx;
  color: #999;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16rpx 0;
  border-bottom: 1rpx solid #f5f5f5;
}

.info-row:last-child {
  border-bottom: none;
}

.info-row .label {
  color: #999;
}

.info-row .value {
  color: #333;
  text-align: right;
}

.price {
  color: #ff4444;
  font-weight: bold;
  font-size: 28rpx;
}
</style>