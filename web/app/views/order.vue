<script setup>
import {h, onMounted, reactive, ref} from "vue"
import {request} from "@/plugins/request.js"
import {message} from "@/plugins/feedback.js"
import {EyeOutlined, SearchOutlined, RedoOutlined} from "@ant-design/icons-vue"
import {NButton, NTag} from "naive-ui"

// 订单状态选项
const statusQueryOptions = {
  ALL: -1,
  UNPAID: 0,
  PAID: 1,
  DELIVERING: 2,
  FINISHED: 3,
  REFUNDING: 4,
  REFUNDED: 5
}
const statusOptions = {
  "-1": {label: "全部", value: statusQueryOptions.ALL, color: null},
  0: {label: "未支付", value: statusQueryOptions.UNPAID, color: "warning"},
  1: {label: "已支付", value: statusQueryOptions.PAID, color: "info"},
  2: {label: "配送中", value: statusQueryOptions.DELIVERING, color: "primary"},
  3: {label: "已完成", value: statusQueryOptions.FINISHED, color: "success"},
  4: {label: "退款中", value: statusQueryOptions.REFUNDING, color: "error"},
  5: {label: "已退款", value: statusQueryOptions.REFUNDED, color: "default"}
}
const orders = ref([])
const order = reactive({})
const query = reactive({
  page: 1,
  size: 10,
  status: statusQueryOptions.ALL,
  quantityMin: null,
  quantityMax: null,
  amountMin: null,
  amountMax: null,
  creationTimeMin: null,
  creationTimeMax: null
})
const loading = ref(false)
const visible = ref(false)
const columns = [
  {
    title: "订单状态",
    key: "status",
    width: "10%",
    render: (row) => h(NTag, {
      type: statusOptions[row.status].color,
      size: "small",
      bordered: false
    }, {default: () => statusOptions[row.status].label})
  },
  {
    title: "商品数量",
    key: "quantity",
    width: "10%",
    align: "center"
  },
  {
    title: "订单金额",
    key: "amount",
    width: "10%",
    render: (row) => `¥${row.amount}`
  },
  {
    title: "下单时间",
    key: "creationTime",
    width: "10%",
    render: (row) => formatDateTime(row.creationTime)
  },
  {
    title: "操作",
    key: "actions",
    render: (row) => h(NButton, {
      size: "small",
      quaternary: true,
      onClick: () => viewDetail(row)
    }, {default: () => "详情", icon: () => h(EyeOutlined)})
  }
]

const fetchOrders = async () => {
  loading.value = true
  let params = {status: query.status}
  if (query.amountMin) {
    params = {...params, amountMin: query.amountMin}
  }
  if (query.amountMax) {
    params = {...params, amountMax: query.amountMax}
  }
  if (query.quantityMin) {
    params = {...params, quantityMin: query.quantityMin}
  }
  if (query.quantityMax) {
    params = {...params, quantityMax: query.quantityMax}
  }
  if (params.creationTimeMin) {
    const date = new Date(params.creationTimeMin)
    if (!isNaN(date.getTime())) {
      params.creationTimeMin = date.toISOString()
    }
  }
  if (params.creationTimeMax) {
    const date = new Date(params.creationTimeMax)
    if (!isNaN(date.getTime())) {
      params.creationTimeMax = date.toISOString()
    }
  }

  const response = await request.get("/admin/order", {params})
  if (response.code === 1) {
    orders.value = response.data
  } else {
    message.error(response.message)
  }
}

const viewDetail = (oldOrder) => {
  Object.assign(order, oldOrder)
  visible.value = true
}

const formatDateTime = (dateString) => {
  if (!dateString) return ""
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return dateString
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  })
}

const setPage = async (page) => {
  query.page = page
  await fetchOrders()
}

const setSize = async (size) => {
  query.size = size
  query.page = 1
  await fetchOrders()
}

const reset = () => {
  query.status = statusQueryOptions.ALL
  query.quantityMin = null
  query.quantityMax = null
  query.amountMin = null
  query.amountMax = null
  query.creationTimeMin = null
  query.creationTimeMax = null
  query.page = 1
  fetchOrders()
}

onMounted(async () => {
  await fetchOrders()
})
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap gap-3">
      <n-select
          v-model:value="query.status"
          :options="Object.entries(statusOptions).map(([_, value]) => ({label: value.label, value: value.value}))"
          placeholder="订单状态"
          clearable
          class="flex-1 min-w-[120px]"/>
      <n-input-group class="flex-1 min-w-[200px]">
        <n-input-number
            v-model:value="query.quantityMin"
            placeholder="数量下限"
            :min="1"
            :step="1"
            clearable
            class="flex-1"/>
        <n-input-number
            v-model:value="query.quantityMax"
            placeholder="数量上限"
            :min="1"
            :step="1"
            clearable
            class="flex-1"/>
      </n-input-group>
      <n-input-group class="flex-1 min-w-[200px]">
        <n-input-number
            v-model:value="query.amountMin"
            placeholder="金额下限"
            :min="0.01"
            :precision="2"
            :step="1"
            clearable
            class="flex-1">
          <template #prefix>¥</template>
        </n-input-number>
        <n-input-number
            v-model:value="query.amountMax"
            placeholder="金额上限"
            :min="0.01"
            :precision="2"
            :step="1"
            clearable
            class="flex-1"
        >
          <template #prefix>¥</template>
        </n-input-number>
      </n-input-group>
      <n-input-group class="flex-1 min-w-[200px]">
        <n-date-picker
            v-model:value="query.creationTimeMin"
            type="date"
            placeholder="开始日期"
            clearable
            class="flex-1"
        />
        <n-date-picker
            v-model:value="query.creationTimeMax"
            type="date"
            placeholder="结束日期"
            clearable
            class="flex-1"
        />
      </n-input-group>
      <n-button @click="reset">
        <template #icon>
          <RedoOutlined/>
        </template>
        重置
      </n-button>
      <n-button type="primary" @click="fetchOrders" :loading="loading">
        <template #icon>
          <SearchOutlined/>
        </template>
        搜索
      </n-button>
    </div>

    <!-- 订单表格 -->
    <n-data-table
        :columns="columns"
        :data="orders"
        :bordered="false"
        :loading="loading"
        max-height="65vh"
        striped
    />
    <div class="flex justify-end mt-4">
      <n-pagination
          v-model:page="query.page"
          v-model:page-size="query.size"
          :page-sizes="[10, 20, 50, 100]"
          show-size-picker
          @update:page="setPage"
          @update:page-size="setSize"
      />
    </div>

    <!-- 订单详情对话框 -->
    <n-modal
        v-model:show="visible"
        :mask-closable="false"
        preset="dialog"
        title="订单详情"
        style="width: 700px"
    >
      <n-card v-if="order" :bordered="false">
        <n-descriptions label-placement="left" bordered column="1">
          <n-descriptions-item label="订单ID">{{ order.id }}</n-descriptions-item>
          <n-descriptions-item label="订单状态">
            <n-tag :type="statusOptions[order.status].color">
              {{ statusOptions[order.status].label }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="商品数量">{{ order.quantity }}</n-descriptions-item>
          <n-descriptions-item label="订单金额">¥{{ order.amount }}</n-descriptions-item>
          <n-descriptions-item label="下单时间">{{ formatDateTime(order.creationTime) }}</n-descriptions-item>
          <n-descriptions-item label="交易编号">{{ order.tradeNumber || "无" }}</n-descriptions-item>
          <n-descriptions-item label="收货人姓名">{{ order.address?.name }}</n-descriptions-item>
          <n-descriptions-item label="联系电话">{{ order.address?.telephone }}</n-descriptions-item>
          <n-descriptions-item label="所在地区">{{ order.address?.region }}</n-descriptions-item>
          <n-descriptions-item label="详细地址">{{ order.address?.detail }}</n-descriptions-item>
          <n-descriptions-item label="商品名称">{{ order.product?.name }}</n-descriptions-item>
          <n-descriptions-item label="商品价格">¥{{ order.product?.price }}</n-descriptions-item>
          <n-descriptions-item label="商品封面">
            <div class="flex flex-wrap gap-2">
              <img
                  v-for="(url, index) in order.product?.covers"
                  :key="index"
                  :src="url"
                  class="w-20 h-20 object-cover rounded"
              />
            </div>
          </n-descriptions-item>
        </n-descriptions>
        <template #footer>
          <div class="flex justify-end">
            <n-button @click="visible = false">关闭</n-button>
          </div>
        </template>
      </n-card>
    </n-modal>
  </div>
</template>

<style scoped>
</style>