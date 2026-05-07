import {createApp} from "vue"
import {createPinia} from "pinia"
import naive from 'naive-ui'
import App from "@/views/app.vue"
import {router} from "@/plugins/router.js"
import "@/assets/app.css"

const app = createApp(App)

app.use(createPinia())
app.use(naive)
app.use(router)

app.mount("#app")
