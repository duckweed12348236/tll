import {computed, ref} from "vue"
import {defineStore} from "pinia"
import {serializer} from "@/plugins/serializer.js"


const USER_KEY = "user"
const TOKEN_KEY = "token"

const useStore = defineStore("user", () => {
    const _user = ref(null)
    const _token = ref("")

    const user = computed({
        get: () => {
            if (_user.value === null) {
                const value = localStorage.getItem(USER_KEY)
                _user.value = value ? serializer.parse(value) : null
            }

            return _user.value
        },
        set: (value) => {
            _user.value = value
            localStorage.setItem(USER_KEY, serializer.stringify(value))
        }
    })

    const token = computed({
        get: () => {
            if (_token.value === "") {
                const value = localStorage.getItem(TOKEN_KEY)
                _token.value = value || ""
            }

            return _token.value
        },
        set: (value) => {
            _token.value = value
            localStorage.setItem(TOKEN_KEY, value)
        }
    })

    const isLogin = computed(() => {
        return user.value !== null && token.value !== ""
    })

    function clear() {
        _user.value = null
        _token.value = ""
        localStorage.removeItem(USER_KEY)
        localStorage.removeItem(TOKEN_KEY)
    }

    return {user, token, isLogin, clear}
})


export {useStore}