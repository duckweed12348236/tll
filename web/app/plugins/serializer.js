import JSONbig from "json-bigint"

const JSON = JSONbig({
    storeAsString: true
})

const serializer = {
    parse: (json) => JSON.parse(json),
    stringify: (obj) => JSON.stringify(obj)
}

export {serializer}