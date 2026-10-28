const serializer = {
    stringify: (obj) => JSON.stringify(obj, (key, value) => {
        if (typeof value === "bigint") {
            return value.toString()
        }
        return value
    }),
    parse: (text) => JSON.parse(text, (key, value) => {
        if (typeof value === "number" &&
            Number.isInteger(value) &&
            (value > Number.MAX_SAFE_INTEGER || value < Number.MIN_SAFE_INTEGER)) {
            value = BigInt(value)
        }
        return value
    })
}

export {serializer}
