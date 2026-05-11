<script setup>
import {onMounted, ref, reactive} from "vue"
import {request} from "@/plugins/request.js"
import {LineChart} from "vue-chart-3"
import {Chart, registerables} from "chart.js"
import {NSelect, NCard, NStatistic, useMessage} from "naive-ui"

Chart.register(...registerables)

const message = useMessage()
const dayOptions = [
  {label: "最近7天", value: 7},
  {label: "最近30天", value: 30},
  {label: "最近60天", value: 60},
  {label: "最近90天", value: 90}
]
const dayOption = ref(7)
const countChart = reactive({
  labels: [],
  datasets: [
    {
      label: "订单成交量",
      data: [],
      borderColor: "rgb(75, 192, 192)",
      backgroundColor: "rgba(75, 192, 192, 0.2)",
      tension: 0.4
    }
  ]
})
const amountChart = reactive({
  labels: [],
  datasets: [
    {
      label: "订单成交额",
      data: [],
      borderColor: "rgb(255, 99, 132)",
      backgroundColor: "rgba(255, 99, 132, 0.2)",
      tension: 0.4
    }
  ]
})
const quantityChart = reactive({
  labels: [],
  datasets: [
    {
      label: "商品销售量",
      data: [],
      borderColor: "rgb(54, 162, 235)",
      backgroundColor: "rgba(54, 162, 235, 0.2)",
      tension: 0.4
    }
  ]
})
const todayCount = ref(0)
const todayAmount = ref(0)
const todayQuantity = ref(0)
const loading = ref(false)

const fetchSummary = async () => {
  loading.value = true
  const response = await request.get("/admin/order/summary", {params: {days: dayOption.value}})
  if (response.code === 1) {
    const labels = []
    const entries = Object.entries(response.data)
    entries.forEach(([key, value]) => {
      labels.push(key)
      countChart.datasets[0].data.push(value.count || 0)
      amountChart.datasets[0].data.push(value.amount || 0)
      quantityChart.datasets[0].data.push(value.quantity || 0)
    })
    countChart.labels = labels
    amountChart.labels = labels
    quantityChart.labels = labels
    todayCount.value = entries[entries.length - 1][1].count || 0
    todayAmount.value = entries[entries.length - 1][1].amount || 0
    todayQuantity.value = entries[entries.length - 1][1].quantity || 0
  } else {
    message.error(response.message)
  }
  loading.value = false
}

const chartOptions = {
  responsive: true,
  plugins: {
    legend: {
      position: "top",
    },
    tooltip: {
      mode: "index",
      intersect: false
    }
  },
  scales: {
    y: {
      beginAtZero: true
    }
  }
}

onMounted(async () => {
  await fetchSummary()
})
</script>

<template>
  <div class="p-4 space-y-6">
    <div class="flex justify-between items-center">
      <n-select
          v-model:value="dayOption"
          :options="dayOptions"
          style="width: 200px"
          @update:value="fetchSummary"/>
    </div>

    <!-- 今日统计 -->
    <div class="flex gap-4">
      <n-card title="今日订单成交量" size="small" class="flex-1">
        <n-statistic :value="todayCount"/>
      </n-card>
      <n-card title="今日订单成交额" size="small" class="flex-1">
        <n-statistic :value="todayAmount" :precision="2">
          <template #prefix>¥</template>
        </n-statistic>
      </n-card>
      <n-card title="今日商品销售量" size="small" class="flex-1">
        <n-statistic :value="todayQuantity"/>
      </n-card>
    </div>

    <!-- 图表 -->
    <n-card title="订单成交量趋势" size="small">
      <LineChart
          :chart-data="countChart"
          :options="chartOptions"
          :height="300"/>
    </n-card>

    <n-card title="订单成交额趋势" size="small">
      <LineChart
          :chart-data="amountChart"
          :options="chartOptions"
          :height="300"/>
    </n-card>

    <n-card title="商品销售量趋势" size="small">
      <LineChart
          :chart-data="quantityChart"
          :options="chartOptions"
          :height="300"/>
    </n-card>
  </div>
</template>

<style scoped>
</style>