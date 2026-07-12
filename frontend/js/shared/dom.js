export function $(selector) {
    return document.querySelector(selector);
}


export function $all(selector) {
    return Array.from(document.querySelectorAll(selector));
}


export function showToast(text, duration = 2600) {
    const toast = $("#toast");
    if (!toast) return;

    toast.textContent = text;
    toast.hidden = false;
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => {
        toast.hidden = true;
    }, duration);
}
