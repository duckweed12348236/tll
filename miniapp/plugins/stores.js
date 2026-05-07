import {ref, computed} from "vue"
import {defineStore} from "pinia"
import {serializer} from "@/plugins/serializer"

const USER_KEY = "USER"
const ACCESS_TOKEN_KEY = "ACCESS_TOKEN"
const REFRESH_TOKEN_KEY = "REFRESH_TOKEN"

const useStore = defineStore("user", () => {
    const _user = ref(null)
    const _access_token = ref("")
    const _refresh_token = ref("")

    function clear() {
        _user.value = null
        _access_token.value = ""
        _refresh_token.value = ""

        uni.removeStorageSync(USER_KEY)
        uni.removeStorageSync(ACCESS_TOKEN_KEY)
        uni.removeStorageSync(REFRESH_TOKEN_KEY)
    }

    const user = computed({
        get: () => {
            if (_user.value === null) {
                const value = uni.getStorageSync(USER_KEY)
                if (value) {
                    _user.value = serializer.parse(value)
                }
            }
            return _user.value
        },
        set: (value) => {
            _user.value = value
            uni.setStorageSync(USER_KEY, serializer.stringify(value))
        }
    })

    const accessToken = computed({
        get: () => {
            if (!_access_token.value) {
                const value = uni.getStorageSync(ACCESS_TOKEN_KEY)
                if (value) {
                    _access_token.value = value
                }
            }
            return _access_token.value
        },
        set: (value) => {
            _access_token.value = value
            uni.setStorageSync(ACCESS_TOKEN_KEY, value)
        }
    })

    const refreshToken = computed({
        get: () => {
            if (!_refresh_token.value) {
                const value = uni.getStorageSync(REFRESH_TOKEN_KEY)
                if (value) {
                    _refresh_token.value = value
                }
            }
            return _refresh_token.value
        },
        set: (value) => {
            _refresh_token.value = value
            uni.setStorageSync(REFRESH_TOKEN_KEY, value)
        }
    })

    return {
        user,
        accessToken,
        refreshToken,
        clear
    }
})


export {useStore}