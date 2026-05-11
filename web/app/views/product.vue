<script setup>
import {h, onMounted, reactive, ref, useTemplateRef} from "vue"
import {request} from "@/plugins/request.js"
import {
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  SearchOutlined,
  StopOutlined
} from "@ant-design/icons-vue"
import {NButton, NInputNumber, NInputGroup, NTag, useDialog, useMessage} from "naive-ui"

const dialog = useDialog()
const message = useMessage()
const form = useTemplateRef("form")
const products = ref([])
const product = reactive({
  id: null,
  name: "",
  price: 0,
  covers: [],
  details: [],
  stock: 0,
  perMaxQuantity: 0
})
const query = reactive({
  page: 1,
  size: 10,
  priceMax: null,
  priceMin: null,
  stockMax: null,
  stockMin: null,
  discontinued: null,
  name: null,
  status: -1
})
const loading = ref(false)
const visible = ref(false)
const action = ref(1)
const statusOptions = [
  {label: "全部", value: -1},
  {label: "已下架", value: 0},
  {label: "在售", value: 1}
]
const columns = [
  {
    title: "商品名称",
    key: "name",
    width: "20%"
  },
  {
    title: "价格",
    key: "price",
    width: "10%",
    render: (row) => `¥${row.price}`
  },
  {
    title: "库存",
    key: "stock",
    width: "10%"
  },
  {
    title: "状态",
    key: "discontinued",
    width: "10%",
    render: (row) => h(NTag, {
      type: row.discontinued ? "error" : "success",
      size: "small",
      bordered: false
    }, {default: () => row.discontinued ? "已下架" : "在售"})
  },
  {
    title: "操作",
    key: "actions",
    render: (row) => h("div", {class: "flex gap-2"}, [
      h(NButton, {
        size: "small",
        quaternary: true,
        onClick: () => openDialog(3, row)
      }, {default: () => "详情", icon: () => h(EyeOutlined)}),
      h(NButton, {
        size: "small",
        quaternary: true,
        onClick: () => openDialog(2, row)
      }, {default: () => "编辑", icon: () => h(EditOutlined)}),
      h(NButton, {
        size: "small",
        quaternary: true,
        type: row.discontinued ? "success" : "warning",
        onClick: () => updateProductStatus(row)
      }, {
        default: () => row.discontinued ? "上架" : "下架",
        icon: () => row.discontinued ? h(PlayCircleOutlined) : h(StopOutlined)
      }),
      h(NButton, {
        size: "small",
        quaternary: true,
        type: "error",
        onClick: () => deleteProduct(row)
      }, {default: () => "删除", icon: () => h(DeleteOutlined)})
    ])
  }
]
const rules = {
  name: [
    {required: true, message: "请输入商品名称", trigger: ["blur", "input"]},
    {max: 200, message: "商品名称长度不能超过200个字符", trigger: ["blur", "input"]}
  ],
  price: [
    {required: true, type: "number", message: "请输入价格", trigger: "blur"},
    {type: "number", min: 0.01, message: "价格必须大于0", trigger: "blur"}
  ],
  stock: [
    {required: true, type: "number", message: "请输入库存数量", trigger: "blur"},
    {type: "number", min: 1, message: "库存必须大于等于1", trigger: "blur"}
  ],
  perMaxQuantity: [
    {required: true, type: "number", message: "请输入单次购买上限", trigger: "blur"},
    {type: "number", min: 1, message: "单次购买上限必须大于等于1", trigger: "blur"}
  ],
  covers: [
    {
      required: true,
      validator: (rule, value) => {
        if (!value || !Array.isArray(value) || value.length < 1) {
          return new Error("至少上传一张封面图片")
        }
        return true
      },
      trigger: ["blur", "change"]
    }
  ],
  details: [
    {
      required: true,
      validator: (rule, value) => {
        if (!value || !Array.isArray(value) || value.length < 1) {
          return new Error("至少上传一张详情图片")
        }
        return true
      },
      trigger: ["blur", "change"]
    }
  ]
}

const fetchProducts = async () => {
  let params = {page: query.page, size: query.size, status: query.status}
  if (query.name) {
    params.name = {...params, name: query.name}
  }
  if (query.priceMin) {
    params.priceMin = {...params, priceMin: query.priceMin}
  }
  if (query.priceMax) {
    params.priceMax = {...params, priceMax: query.priceMax}
  }
  if (query.stockMin) {
    params.stockMin = {...params, stockMin: query.stockMin}
  }
  if (query.stockMax) {
    params.stockMax = {...params, stockMax: query.stockMax}
  }

  loading.value = true
  const response = await request.get("/admin/product", {params})
  if (response.code === 1) {
    products.value = response.data.map(product => ({...product, price: Number(product.price)}))
  } else {
    message.error(response.message)
  }
  loading.value = false
}

const setPage = async (page) => {
  query.page = page
  await fetchProducts()
}

const setSize = async (size) => {
  query.size = size
  await fetchProducts()
}

const createProduct = async (product) => {
  const response = await request.post("/admin/product", product)
  if (response.code === 1) {
    await fetchProducts()
  } else {
    message.error(response.message)
  }
}

const updateProduct = async (product, productId) => {
  const response = await request.put("/admin/product", product, {path: productId})
  if (response.code === 1) {
    await fetchProducts()
  } else {
    message.error(response.message)
  }
}

const updateProductStatus = async (product) => {
  const isDiscontinued = product.discontinued
  dialog.warning({
    title: isDiscontinued ? "确认上架" : "确认下架",
    content: `确定要${isDiscontinued ? "上架" : "下架"}商品 "${product.name}" 吗？`,
    positiveText: "确认",
    negativeText: "取消",
    onPositiveClick: async () => {
      const response = await request.patch("/admin/product", {}, {path: product.id})
      if (response.code === 1) {
        await fetchProducts()
      } else {
        message.error(response.message)
      }
    }
  })
}

const deleteProduct = (product) => {
  dialog.warning({
    title: "确认删除",
    content: `确定要删除商品 "${product.name}" 吗？此操作不可恢复。`,
    positiveText: "确认",
    negativeText: "取消",
    onPositiveClick: async () => {
      const response = await request.delete("/admin/product", {path: product.id})
      if (response.code === 1) {
        await fetchProducts()
      } else {
        message.error(response.message)
      }
    }
  })
}

const uploadImage = async (options, attrName) => {
  options.onProgress({percent: 0})
  const response = await request.upload("/admin/image", options.file.file, "images")
  if (response.code === 1) {
    options.onProgress({percent: 100})
    product[attrName].push(response.data[0])
    options.onFinish()
  } else {
    message.error(response.message)
    options.onError()
  }
}

const removeImage = (index, attrName) => {
  product[attrName].splice(index, 1)
}

const openDialog = (option, oldProduct = null) => {
  action.value = option
  switch (option) {
    case 1:
      Object.assign(product, {
        id: null,
        name: "",
        price: null,
        covers: [],
        details: [],
        stock: null,
        perMaxQuantity: null
      })
      break
    case 2:
      Object.assign(product, {
        id: oldProduct.id,
        name: oldProduct.name,
        price: oldProduct.price,
        covers: [...oldProduct.covers],
        details: [...oldProduct.details],
        stock: oldProduct.stock,
        perMaxQuantity: oldProduct.perMaxQuantity
      })
      break
    case 3:
      Object.assign(product, oldProduct)
      break
  }

  visible.value = true
}

const submit = async () => {
  try {
    await form.value.validate()
    const oldProduct = {
      name: product.name,
      price: product.price,
      covers: product.covers,
      details: product.details,
      stock: product.stock,
      perMaxQuantity: product.perMaxQuantity
    }
    if (action.value === 1) {
      await createProduct(oldProduct)
    } else if (action.value === 2) {
      await updateProduct(oldProduct, product.id)
    }
    visible.value = false
  } catch (errors) {
  }
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

onMounted(async () => {
  await fetchProducts()
})
</script>

<template>
  <div class="mb-4 flex items-center gap-2">
    <n-input
        v-model:value="query.name"
        placeholder="输入商品名称以搜索"
        @keyup.enter="fetchProducts"
        clearable
        class="flex-2"/>
    <n-select
        v-model:value="query.status"
        :options="statusOptions"
        placeholder="商品状态"
        class="flex-1 min-w-[120px]"/>
    <n-input-group class="flex-1">
      <n-input-number
          v-model:value="query.priceMin"
          placeholder="价格下限"
          :min="0"
          :precision="2"
          :step="1"
          clearable/>
      <n-input-number
          v-model:value="query.priceMax"
          placeholder="价格上限"
          :min="0"
          :precision="2"
          :step="1"
          clearable/>
    </n-input-group>
    <n-input-group class="flex-1">
      <n-input-number
          v-model:value="query.stockMin"
          placeholder="库存下限"
          :min="0"
          :step="1"
          clearable/>
      <n-input-number
          v-model:value="query.stockMax"
          placeholder="库存上限"
          :min="0"
          :step="1"
          clearable/>
    </n-input-group>
    <n-button type="primary" @click="fetchProducts" :loading="loading" class="flex-none">
      <template #icon>
        <SearchOutlined/>
      </template>
      搜索
    </n-button>
    <n-button type="primary" @click="() => openDialog(1)" class="flex-none">
      <template #icon>
        <PlusOutlined/>
      </template>
      新增商品
    </n-button>
  </div>
  <!-- 商品表格 -->
  <n-data-table
      :columns="columns"
      :data="products"
      :bordered="false"
      max-height="65vh"
      striped
      :loading="loading"/>
  <div class="mt-4 flex justify-end">
    <n-pagination
        v-model:page="query.page"
        v-model:page-size="query.size"
        :page-sizes="[10, 20, 50, 100]"
        show-size-picker
        @update:page="setPage"
        @update:page-size="setSize"/>
  </div>

  <!-- 新增/编辑/详情对话框 -->
  <n-modal
      v-model:show="visible"
      :mask-closable="false"
      :title="action === 1 ? '新增商品' : action === 2 ? '编辑商品' : '商品详情'"
      preset="dialog"
      style="width: 800px">
    <n-card :bordered="false">
      <template #footer>
        <div v-if="action !== 3" class="flex justify-end gap-3">
          <n-button @click="() => visible = false">取消</n-button>
          <n-button type="primary" @click="submit">确认</n-button>
        </div>
        <div v-else class="flex justify-end">
          <n-button @click="() => visible = false">关闭</n-button>
        </div>
      </template>

      <div class="max-h-120 overflow-auto pr-2">
        <n-descriptions
            v-if="action === 3"
            label-placement="left"
            bordered
            column="1">
          <n-descriptions-item label="商品名称">{{ product.name }}</n-descriptions-item>
          <n-descriptions-item label="价格">¥{{ product.price }}</n-descriptions-item>
          <n-descriptions-item label="库存">{{ product.stock }}</n-descriptions-item>
          <n-descriptions-item label="单次购买上限">{{ product.perMaxQuantity }}</n-descriptions-item>
          <n-descriptions-item label="状态">
            <n-tag :type="product.discontinued ? 'error' : 'success'" size="small" bordered>
              {{ product.discontinued ? "已下架" : "在售" }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="创建时间">{{ formatDateTime(product.creationTime) }}</n-descriptions-item>
          <n-descriptions-item label="封面">
            <n-carousel show-arrow centered-slides class="max-w-60">
              <n-image
                  v-for="(url, index) in product.covers"
                  :key="index"
                  :src="url"/>
            </n-carousel>
          </n-descriptions-item>
          <n-descriptions-item label="详情">
            <n-carousel show-arrow centered-slides class="max-w-60">
              <n-image
                  v-for="(url, index) in product.details"
                  :key="index"
                  :src="url"/>
            </n-carousel>
          </n-descriptions-item>
        </n-descriptions>

        <n-form
            v-else
            ref="form"
            :model="product"
            :rules="rules"
            label-placement="left"
            label-width="auto"
            require-mark-placement="right-hanging">
          <n-form-item label="商品名称" path="name">
            <n-input v-model:value="product.name" placeholder="请输入商品名称" maxlength="200" show-count/>
          </n-form-item>
          <n-form-item label="价格" path="price">
            <n-input-number
                v-model:value="product.price"
                placeholder="请输入价格"
                :min="0"
                :precision="2"
                :step="1"
                class="w-full">
              <template #prefix>¥</template>
            </n-input-number>
          </n-form-item>
          <n-form-item label="库存" path="stock">
            <n-input-number
                v-model:value="product.stock"
                placeholder="请输入库存数量"
                :min="0"
                class="w-full"/>
          </n-form-item>
          <n-form-item label="单次购买上限" path="perMaxQuantity">
            <n-input-number
                v-model:value="product.perMaxQuantity"
                placeholder="请输入单次购买最大数量"
                :min="0"
                class="w-full"/>
          </n-form-item>
          <n-form-item label="封面" path="covers">
            <n-upload
                multiple
                :default-file-list="product.covers.map(url => ({url, name: url, status: 'finished'}))"
                @remove="({index}) => removeImage(index, 'covers')"
                :custom-request="(options) => uploadImage(options, 'covers')"
                list-type="image-card"
                :max="5">
              点击上传
            </n-upload>
          </n-form-item>
          <n-form-item label="详情" path="details">
            <n-upload
                multiple
                :default-file-list="product.details.map(url => ({url, name: url, status: 'finished'}))"
                @remove="(options) => removeImage(options, 'details')"
                :custom-request="(options) => uploadImage(options, 'details')"
                list-type="image-card"
                :max="10">
              点击上传
            </n-upload>
          </n-form-item>
        </n-form>
      </div>
    </n-card>
  </n-modal>
</template>

<style scoped>
.n-upload-trigger {
  width: 100px;
  height: 100px;
}
</style>