import {createRouter, createWebHistory} from "vue-router"
import {h} from "vue"
import {ShoppingCartOutlined, DashboardOutlined, OrderedListOutlined} from "@ant-design/icons-vue"

const routes = [
    {
        path: "/",
        name: "main",
        component: () => import("@/views/main.vue"),
        children: [
            {
                path: "",
                name: "dashboard",
                component: () => import("@/views/dashboard.vue"),
                meta: {
                    label: "概览",
                    icon: () => h(DashboardOutlined)
                }
            },
            {
                path: "product",
                name: "product",
                component: () => import("@/views/product.vue"),
                meta: {
                    label: "商品",
                    icon: () => h(ShoppingCartOutlined)
                }
            },
            {
                path: "order",
                name: "order",
                component: () => import("@/views/order.vue"),
                meta: {
                    label: "订单",
                    icon: () => h(OrderedListOutlined)
                }
            }
        ]
    }
]

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: routes
})

router.beforeEach((to, from, next) => {
    return next()
})

export {router, routes}