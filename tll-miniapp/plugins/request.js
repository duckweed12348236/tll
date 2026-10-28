import {useStore} from "@/plugins/stores"
import {SERVER_URL} from "@/config"

function parseSnakeCaseToCamelCase(obj) {
    if (typeof obj !== "object" || obj === null || obj === {}) {
        return obj
    }

    if (Array.isArray(obj)) {
        return obj.map(item => parseSnakeCaseToCamelCase(item))
    }

    const newObj = {}
    Object.entries(obj).forEach(([key, value]) => {
        const [, prefix, middle, suffix] = key.match(/^(_*)(.*?)(_*)$/)
        const newKeyMiddle = middle.split("_").reduce((acc, word, index) => {
            if (index === 0) {
                return word
            }
            return acc + (word ? word.charAt(0).toUpperCase() + word.slice(1) : "")
        }, "")
        const newKey = prefix + newKeyMiddle + suffix
        newObj[newKey] = parseSnakeCaseToCamelCase(value)
    })

    return newObj
}

function parseCamelCaseToSnakeCase(obj) {
    if (typeof obj !== "object" || obj === null || obj === {}) {
        return obj
    }

    if (Array.isArray(obj)) {
        return obj.map(item => parseCamelCaseToSnakeCase(item))
    }

    const newObj = {}

    Object.entries(obj).forEach(([key, value]) => {
        const [, prefix, middle, suffix] = key.match(/^(_*)(.*?)(_*)$/)
        const snakeMiddle = middle.replace(/[A-Z]/g, match => `_${match.toLowerCase()}`)
        const newKey = prefix + snakeMiddle + suffix
        newObj[newKey] = parseCamelCaseToSnakeCase(value)
    })

    return newObj
}

function parseBigInt(obj) {
    if (typeof obj !== "object" || obj === null || obj === {}) {
        return obj
    }

    if (Array.isArray(obj)) {
        return obj.map(item => parseBigInt(item))
    }

    Object.entries(obj).forEach(([key, value]) => {
        if (typeof value === "number" &&
            Number.isInteger(value) &&
            (value > Number.MAX_SAFE_INTEGER || value < Number.MIN_SAFE_INTEGER)) {
            obj[key] = BigInt(value)
        } else if (Array.isArray(value)) {
            obj[key] = parseBigInt(value)
        }
    })

    return obj
}

function stringifyBigInt(obj) {
    if (typeof obj !== "object" || obj === null || obj === {}) {
        return obj
    }

    if (Array.isArray(obj)) {
        return obj.map(item => stringifyBigInt(item))
    }

    Object.entries(obj).forEach(([key, value]) => {
        if (typeof value === "bigint") {
            obj[key] = value.toString()
        } else if (Array.isArray(value)) {
            obj[key] = stringifyBigInt(value)
        }
    })

    return obj
}

class Request {
    async updateToken() {
        const store = useStore()

        if (!store.hasOwnProperty("refreshToken")) {
            return null
        }

        try {
            const response = await uni.request({
                method: "POST",
                url: `${SERVER_URL}/user/access-token`,
                header: {
                    "Access-Control-Allow-Origin": true
                },
                data: {value: store.refreshToken}
            })

            if (response.statusCode === 401) {
                return null
            }

            return response.data
        } catch (e) {
            return null
        }
    }

    exit() {
        const store = useStore()
        store.clear()
        uni.showToast({
            title: "登录过期，请重新登录",
            icon: "none"
        })
        uni.redirectTo({
            url: "/pages/login"
        })
    }

    async send(method, url, data = {}, path = "") {
        const store = useStore()
        try {
            const response = await uni.request({
                method: method,
                url: path === "" ? `${SERVER_URL}${url}` : `${SERVER_URL}${url}/${typeof path === "bigint" ? path.toString() : path}`,
                header: {
                    "Authorization": `Bearer ${store.accessToken}`,
                    "Access-Control-Allow-Origin": true
                },
                data: stringifyBigInt(parseCamelCaseToSnakeCase(data))
            })

            switch (response.statusCode) {
                case 403:
                    const token = await this.updateToken()
                    if (token === null) {
                        this.exit()
                        return
                    }
                    store.accessToken = token
                    return await this.send(method, url, data, path)
                case 401:
                    this.exit()
                    return
                default:
                    if (response.statusCode < 200 || response.statusCode >= 300) {
                        return {
                            code: 0,
                            message: response.data.detail,
                            data: null
                        }
                    }

                    return {
                        code: 1,
                        message: null,
                        data: parseBigInt(parseSnakeCaseToCamelCase(response.data))
                    }
            }
        } catch (error) {
            return {
                code: 0,
                message: "请求失败",
                data: null
            }
        }
    }

    async get(url, params, path = "") {
        return await this.send("GET", url, params, path)
    }

    async post(url, data, path = "") {
        return await this.send("POST", url, data, path)
    }

    async put(url, data, path = "") {
        return await this.send("PUT", url, data, path)
    }

    async delete(url, path = "") {
        return await this.send("DELETE", url, {}, path)
    }
}

const request = new Request()

export {request}