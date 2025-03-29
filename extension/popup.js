document.addEventListener("DOMContentLoaded", () => {
    chrome.storage.local.get("authToken", (data) => {
        document.getElementById("token").textContent = data.authToken || "No token captured yet.";
    });
});