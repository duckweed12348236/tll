import axios from "axios"
import qs from "qs"
import {serializer} from "@/plugins/serializer.js"
import {SERVER_URL} from "@/config.js"

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
        newObj[newKey] = parseSnakeCaseToCamelCase(value)
    })

    return newObj
}

class Request {
    constructor() {
        this.instance = axios.create({
            baseURL: SERVER_URL,
            paramsSerializer: (params) => qs.stringify(params, {arrayFormat: "repeat"}),
            transformResponse: (text, headers) => {
                if (headers["content-type"].includes("application/json")) {
                    return serializer.parse(text)
                }
                return text
            },
            adapter: "fetch"
        })

        this.instance.interceptors.request.use(config => {
            return config
        })
    }


    async send(method, url, data = null, {params = {}, path = "", timeout = 6000, setProgress = null} = {}) {
        data = (data instanceof FormData) ? data : parseCamelCaseToSnakeCase(data)
        params = parseCamelCaseToSnakeCase(params)
        url = path === "" ? url : `${url}/${path}`

        try {
            let config = {timeout}

            if (setProgress) {
                config = {
                    ...config,
                    onUploadProgress: (progressEvent) => {
                        setProgress(progressEvent.progress)
                    }
                }
            }

            const response = await this.instance({method, url, data, params}, config)
            return {code: 1, message: null, data: parseSnakeCaseToCamelCase(response.data)}
        } catch (error) {
            if (error.hasOwnProperty("response")) {
                return {code: 0, message: error.response.data.detail, data: null}
            }
            return {code: 0, message: "请求失败", data: null}
        }
    }

    async get(url, {params = {}, path = ""} = {}) {
        return await this.send("get", url, null, {params, path})
    }

    async post(url, data, {params = {}, path = ""} = {}) {
        return await this.send("post", url, data, {params, path})
    }

    async put(url, data, {params = {}, path = ""} = {}) {
        return await this.send("put", url, data, {params, path})
    }

    async patch(url, data, {params = {}, path = ""} = {}) {
        return await this.send("patch", url, data, {params, path})
    }

    async delete(url, {params = {}, path = ""} = {}) {
        return await this.send("delete", url, null, {params, path})
    }

    async upload(url, files, name, {params = {}, path = "", setProgress = null} = {}) {
        const data = new FormData()
        if (Array.isArray(files)) {
            files.forEach(file => {
                data.append(name, file)
            })
        } else {
            data.append(name, files)
        }
        return await this.send("post", url, data, {params, path, timeout: 1000 * 60 * 5, setProgress})
    }
}

const request = new Request()

export {request}