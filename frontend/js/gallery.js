import * as THREE from "../vendor/three.module.js";

const ARTIFACTS = [
    {
        id: "brush",
        name: "湖笔",
        label: "笔",
        summary: "笔锋圆健，适合中锋行笔与楷书、行书练习。",
        detail: "毛笔重在尖、齐、圆、健。轻按是铺毫，提起见锋；一支合手的笔，能让笔法的变化更清楚地呈现出来。"
    },
    {
        id: "ink",
        name: "徽墨",
        label: "墨",
        summary: "墨色可分焦、浓、重、淡、清，层次来自加水与运笔。",
        detail: "好墨宜细研慢磨。书写时不只追求黑，更要观察润、枯、浓、淡之间的节奏。"
    },
    {
        id: "paper",
        name: "宣纸",
        label: "纸",
        summary: "生宣吸墨、渗化明显；熟宣较易控制，适合工整书写。",
        detail: "纸性会直接改变线条边缘和墨色层次。初学临帖可先感受纸面对笔锋速度与水分的反馈。"
    },
    {
        id: "inkstone",
        name: "端砚",
        label: "砚",
        summary: "砚用于蓄墨、研墨，也是文房审美中沉静的一环。",
        detail: "端砚石质细腻，研墨时以轻、慢、匀为宜。砚台并非只是容器，它决定了墨液能否保持稳定。"
    }
];

function createLabelTexture(text) {
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 128;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "rgba(255, 252, 245, 0.9)";
    ctx.fillRect(14, 26, 228, 76);
    ctx.strokeStyle = "rgba(161, 58, 45, 0.7)";
    ctx.strokeRect(14, 26, 228, 76);
    ctx.fillStyle = "#241d17";
    ctx.font = "38px serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text, 128, 64);
    return new THREE.CanvasTexture(canvas);
}

function addNamePlate(scene, text, position) {
    const material = new THREE.SpriteMaterial({
        map: createLabelTexture(text),
        transparent: true,
        depthWrite: false
    });
    const sprite = new THREE.Sprite(material);
    sprite.position.set(...position);
    sprite.scale.set(1.05, 0.53, 1);
    scene.add(sprite);
}

function markInteractive(object, artifact) {
    object.traverse((child) => {
        if (child.isMesh) {
            child.userData.artifactId = artifact.id;
            child.userData.baseEmissive = child.material.emissive
                ? child.material.emissive.clone()
                : null;
        }
    });
    return object;
}

function createBrush(artifact) {
    const group = new THREE.Group();
    const bamboo = new THREE.MeshStandardMaterial({ color: "#a87536", roughness: 0.52, metalness: 0.08 });
    const bristle = new THREE.MeshStandardMaterial({ color: "#e0d0a8", roughness: 0.96 });
    const inkTip = new THREE.MeshStandardMaterial({ color: "#221c18", roughness: 0.9 });
    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.13, 2.15, 24), bamboo);
    const ferrule = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.16, 0.18, 24), new THREE.MeshStandardMaterial({ color: "#73501f", metalness: 0.22, roughness: 0.4 }));
    const hairs = new THREE.Mesh(new THREE.ConeGeometry(0.2, 0.95, 28), bristle);
    const tip = new THREE.Mesh(new THREE.ConeGeometry(0.055, 0.32, 20), inkTip);
    shaft.position.y = 1.15;
    ferrule.position.y = 0.1;
    hairs.position.y = -0.45;
    tip.position.y = -1.06;
    group.add(shaft, ferrule, hairs, tip);
    group.rotation.z = -0.34;
    group.position.set(-2.15, 1.65, 0.1);
    return markInteractive(group, artifact);
}

function createInk(artifact) {
    const group = new THREE.Group();
    const body = new THREE.Mesh(
        new THREE.BoxGeometry(1.1, 0.22, 0.56, 4, 1, 3),
        new THREE.MeshStandardMaterial({ color: "#151313", roughness: 0.36, metalness: 0.12 })
    );
    const face = new THREE.Mesh(
        new THREE.PlaneGeometry(0.78, 0.18),
        new THREE.MeshBasicMaterial({ color: "#b99a55" })
    );
    face.position.set(0, 0.116, 0);
    face.rotation.x = -Math.PI / 2;
    group.add(body, face);
    group.rotation.y = -0.4;
    group.position.set(-0.15, 0.9, 0.2);
    return markInteractive(group, artifact);
}

function createPaper(artifact) {
    const group = new THREE.Group();
    const paper = new THREE.Mesh(
        new THREE.PlaneGeometry(2.35, 1.7),
        new THREE.MeshStandardMaterial({ color: "#f4ecdc", roughness: 0.96, side: THREE.DoubleSide })
    );
    paper.rotation.x = -Math.PI / 2;
    paper.position.y = 0.84;
    const inkLineMaterial = new THREE.MeshBasicMaterial({ color: "#27211d", transparent: true, opacity: 0.84 });
    for (let index = 0; index < 4; index += 1) {
        const stroke = new THREE.Mesh(new THREE.PlaneGeometry(0.05, 0.64 - index * 0.05), inkLineMaterial);
        stroke.rotation.x = -Math.PI / 2;
        stroke.position.set(-0.62 + index * 0.38, 0.848, 0.05);
        group.add(stroke);
    }
    group.add(paper);
    group.rotation.y = 0.22;
    group.position.set(1.65, 0, 0.7);
    return markInteractive(group, artifact);
}

function createInkstone(artifact) {
    const group = new THREE.Group();
    const material = new THREE.MeshStandardMaterial({ color: "#362c28", roughness: 0.65, metalness: 0.1 });
    const stone = new THREE.Mesh(new THREE.CylinderGeometry(0.84, 0.96, 0.28, 48), material);
    stone.scale.z = 0.72;
    const pool = new THREE.Mesh(
        new THREE.CircleGeometry(0.42, 40),
        new THREE.MeshStandardMaterial({ color: "#090909", roughness: 0.18, metalness: 0.3 })
    );
    pool.rotation.x = -Math.PI / 2;
    pool.position.y = 0.15;
    group.add(stone, pool);
    group.position.set(1.55, 0.98, -1.1);
    return markInteractive(group, artifact);
}

function createScene(canvas, onSelect) {
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog("#181310", 7, 16);
    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 40);
    const target = new THREE.Vector3(0, 1, 0);
    const state = {
        theta: -0.22,
        phi: 1.13,
        radius: 8.2,
        isDragging: false,
        startX: 0,
        startY: 0,
        lastX: 0,
        lastY: 0,
        activeId: "brush"
    };

    scene.add(new THREE.HemisphereLight("#f3dfbd", "#1b1411", 1.65));
    const keyLight = new THREE.DirectionalLight("#ffe0a6", 2.8);
    keyLight.position.set(-4, 7, 4);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.set(1024, 1024);
    scene.add(keyLight);
    const warmLight = new THREE.PointLight("#b84a32", 14, 8, 2);
    warmLight.position.set(2, 3, -3);
    scene.add(warmLight);

    const floor = new THREE.Mesh(
        new THREE.CircleGeometry(9, 72),
        new THREE.MeshStandardMaterial({ color: "#201815", roughness: 0.94, metalness: 0.02 })
    );
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);

    const table = new THREE.Mesh(
        new THREE.CylinderGeometry(3.45, 3.55, 0.42, 56),
        new THREE.MeshStandardMaterial({ color: "#5a3922", roughness: 0.6, metalness: 0.05 })
    );
    table.position.y = 0.55;
    table.castShadow = true;
    table.receiveShadow = true;
    scene.add(table);

    const rim = new THREE.Mesh(
        new THREE.TorusGeometry(3.28, 0.045, 12, 56),
        new THREE.MeshStandardMaterial({ color: "#b98546", roughness: 0.38, metalness: 0.3 })
    );
    rim.position.y = 0.79;
    rim.rotation.x = Math.PI / 2;
    scene.add(rim);

    const objects = [
        createBrush(ARTIFACTS[0]),
        createInk(ARTIFACTS[1]),
        createPaper(ARTIFACTS[2]),
        createInkstone(ARTIFACTS[3])
    ];
    objects.forEach((object) => {
        object.castShadow = true;
        object.receiveShadow = true;
        scene.add(object);
    });
    addNamePlate(scene, "湖笔", [-2.35, 3.35, 0.1]);
    addNamePlate(scene, "徽墨", [-0.12, 1.48, 0.25]);
    addNamePlate(scene, "宣纸", [1.66, 1.27, 0.7]);
    addNamePlate(scene, "端砚", [1.58, 1.7, -1.08]);

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const setSelection = (id) => {
        state.activeId = id;
        objects.forEach((object) => {
            object.traverse((child) => {
                if (!child.isMesh || !child.material?.emissive) return;
                const selected = child.userData.artifactId === id;
                child.material.emissive.set(selected ? "#5a1f16" : "#000000");
                child.material.emissiveIntensity = selected ? 0.35 : 0;
            });
        });
        const artifact = ARTIFACTS.find((item) => item.id === id);
        if (artifact) onSelect(artifact);
    };

    function updateCamera() {
        const sinPhi = Math.sin(state.phi);
        camera.position.set(
            target.x + state.radius * sinPhi * Math.sin(state.theta),
            target.y + state.radius * Math.cos(state.phi),
            target.z + state.radius * sinPhi * Math.cos(state.theta)
        );
        camera.lookAt(target);
    }

    function resize() {
        const width = Math.max(canvas.clientWidth, 1);
        const height = Math.max(canvas.clientHeight, 1);
        if (canvas.width !== width || canvas.height !== height) {
            renderer.setSize(width, height, false);
            camera.aspect = width / height;
            camera.updateProjectionMatrix();
        }
    }

    function animate() {
        resize();
        objects[0].rotation.y += 0.0015;
        objects[1].rotation.y += 0.002;
        objects[3].rotation.y -= 0.001;
        updateCamera();
        renderer.render(scene, camera);
    }

    canvas.addEventListener("pointerdown", (event) => {
        state.isDragging = true;
        state.startX = event.clientX;
        state.startY = event.clientY;
        state.lastX = event.clientX;
        state.lastY = event.clientY;
        canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener("pointermove", (event) => {
        if (!state.isDragging) return;
        const dx = event.clientX - state.lastX;
        const dy = event.clientY - state.lastY;
        state.lastX = event.clientX;
        state.lastY = event.clientY;
        state.theta -= dx * 0.008;
        state.phi = THREE.MathUtils.clamp(state.phi + dy * 0.008, 0.62, 1.48);
    });
    canvas.addEventListener("pointerup", (event) => {
        const moved = Math.abs(event.clientX - state.startX) + Math.abs(event.clientY - state.startY) > 3;
        state.isDragging = false;
        if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
        if (moved) return;
        const rect = canvas.getBoundingClientRect();
        pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        raycaster.setFromCamera(pointer, camera);
        const hit = raycaster.intersectObjects(objects, true).find((item) => item.object.userData.artifactId);
        if (hit) setSelection(hit.object.userData.artifactId);
    });
    canvas.addEventListener("wheel", (event) => {
        event.preventDefault();
        state.radius = THREE.MathUtils.clamp(state.radius + event.deltaY * 0.008, 5.6, 11);
    }, { passive: false });

    setSelection("brush");
    return {
        setActive(active) {
            if (active) renderer.setAnimationLoop(animate);
            else renderer.setAnimationLoop(null);
        },
        select: setSelection,
        resize
    };
}

export function initGallery() {
    const canvas = document.querySelector("#galleryCanvas");
    const cards = document.querySelector("#galleryArtifactList");
    const title = document.querySelector("#galleryArtifactTitle");
    const summary = document.querySelector("#galleryArtifactSummary");
    const detail = document.querySelector("#galleryArtifactDetail");
    if (!canvas || !cards || !title || !summary || !detail) return null;

    function selectArtifact(artifact) {
        title.textContent = artifact.name;
        summary.textContent = artifact.summary;
        detail.textContent = artifact.detail;
        cards.querySelectorAll("[data-artifact-id]").forEach((card) => {
            card.classList.toggle("is-active", card.dataset.artifactId === artifact.id);
        });
    }

    cards.innerHTML = ARTIFACTS.map((artifact) => `
        <button class="gallery-artifact-card" type="button" data-artifact-id="${artifact.id}">
            <span>${artifact.label}</span>
            <strong>${artifact.name}</strong>
        </button>
    `).join("");

    const controller = createScene(canvas, selectArtifact);
    cards.addEventListener("click", (event) => {
        const card = event.target.closest("[data-artifact-id]");
        if (!card) return;
        controller.select(card.dataset.artifactId);
    });
    window.addEventListener("resize", controller.resize);
    return controller;
}
