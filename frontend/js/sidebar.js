import { classicWorks } from "../data/calligraphy.js";
import { recentPractices } from "../data/history.js";

function renderList(container, items) {
    container.innerHTML = items
        .map((item) => `<li><button type="button" data-history-id="${item.id}">${item.title}</button></li>`)
        .join("");
}

export function initSidebar() {
    const sidebar = document.querySelector("#sidebar");
    const menuButton = document.querySelector("#menuButton");
    const scrim = document.querySelector("#sidebarScrim");
    const classicWorksNode = document.querySelector("#classicWorks");
    const recentPracticesNode = document.querySelector("#recentPractices");
    const navItems = document.querySelectorAll(".nav-item");

    renderList(classicWorksNode, classicWorks);
    renderList(recentPracticesNode, recentPractices);

    const openSidebar = () => {
        sidebar.classList.add("is-open");
        scrim.hidden = false;
    };

    const closeSidebar = () => {
        sidebar.classList.remove("is-open");
        scrim.hidden = true;
    };

    menuButton.addEventListener("click", openSidebar);
    scrim.addEventListener("click", closeSidebar);

    navItems.forEach((item) => {
        item.addEventListener("click", () => {
            navItems.forEach((nav) => nav.classList.remove("nav-item--active"));
            item.classList.add("nav-item--active");
            closeSidebar();
        });
    });

    window.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeSidebar();
        }
    });
}
