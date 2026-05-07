import {fileURLToPath, URL} from "node:url"

import {defineConfig} from "vite"
import vue from "@vitejs/plugin-vue"
import vueDevTools from "vite-plugin-vue-devtools"
import {NaiveUiResolver} from "unplugin-vue-components/resolvers"
import Components from "unplugin-vue-components/vite"
import AutoImport from "unplugin-auto-import/vite"
import tailwindcss from "@tailwindcss/vite"

export default defineConfig({
    plugins: [
        vue(),
        vueDevTools(),
        tailwindcss(),
        AutoImport({
            imports: [
                "vue",
                {
                    "naive-ui": [
                        "useDialog",
                        "useMessage",
                        "useNotification",
                        "useLoadingBar"
                    ]
                }
            ]
        }),
        Components({
            resolvers: [NaiveUiResolver()]
        })
    ],
    resolve: {
        alias: {
            "@": fileURLToPath(new URL("./app", import.meta.url))
        }
    }
})
