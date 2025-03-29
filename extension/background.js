chrome.webRequest.onBeforeSendHeaders.addListener(
    function (details) {
        console.log(details.requestHeaders)

        let authHeader = details.requestHeaders.find(header => header.name.toLowerCase() === "authorization");

        if (details.url.includes('momentica'))
        {
            if (authHeader)
            {
                // Store token in Chrome storage
                chrome.storage.local.set({authToken: authHeader.value});
            }
        }

        return {requestHeaders: details.requestHeaders};
    },
    {urls: ["<all_urls>"]},
    ["requestHeaders"]
);
