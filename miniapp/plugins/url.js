const handleUrls = (urls) => {
    if (urls.length === 0) {
        return []
    }

    const newUrls = []
    for (const url of urls) {
        newUrls.push(url.replace(/\\/g, "/"))
    }
    return newUrls
}

export {handleUrls}