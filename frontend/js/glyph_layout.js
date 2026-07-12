const DEFAULT_INK_THRESHOLD = 238;
const DEFAULT_PADDING_RATIO = 0.1;

function inspectInk(imageData, width, height, threshold = DEFAULT_INK_THRESHOLD) {
    const pixels = imageData.data;
    let left = width;
    let top = height;
    let right = -1;
    let bottom = -1;
    let inkPixels = 0;

    for (let y = 0; y < height; y += 1) {
        for (let x = 0; x < width; x += 1) {
            const offset = (y * width + x) * 4;
            const alpha = pixels[offset + 3];
            const brightness = (pixels[offset] * 0.299) + (pixels[offset + 1] * 0.587) + (pixels[offset + 2] * 0.114);
            if (alpha < 24 || brightness >= threshold) continue;

            inkPixels += 1;
            left = Math.min(left, x);
            top = Math.min(top, y);
            right = Math.max(right, x);
            bottom = Math.max(bottom, y);
        }
    }

    if (right < left || bottom < top) {
        return { left: 0, top: 0, width, height, inkPixels: 0 };
    }

    return {
        left,
        top,
        width: right - left + 1,
        height: bottom - top + 1,
        inkPixels
    };
}

function makePaperTransparent(imageData, threshold = DEFAULT_INK_THRESHOLD) {
    const pixels = imageData.data;
    for (let offset = 0; offset < pixels.length; offset += 4) {
        const brightness = (pixels[offset] * 0.299) + (pixels[offset + 1] * 0.587) + (pixels[offset + 2] * 0.114);
        if (brightness >= threshold) {
            pixels[offset + 3] = 0;
        } else if (brightness > threshold - 22) {
            // Keep anti-aliased stroke edges while fading the pale paper around them.
            pixels[offset + 3] = Math.round(pixels[offset + 3] * ((threshold - brightness) / 22));
        }
    }
}

function createGlyphFrame(image) {
    const sourceWidth = image.naturalWidth || image.width;
    const sourceHeight = image.naturalHeight || image.height;
    if (!sourceWidth || !sourceHeight) return null;

    const sourceCanvas = document.createElement("canvas");
    sourceCanvas.width = sourceWidth;
    sourceCanvas.height = sourceHeight;
    const sourceContext = sourceCanvas.getContext("2d", { willReadFrequently: true });
    if (!sourceContext) return null;

    sourceContext.drawImage(image, 0, 0, sourceWidth, sourceHeight);
    let bounds = { left: 0, top: 0, width: sourceWidth, height: sourceHeight };
    let inkPixels = null;
    try {
        const imageData = sourceContext.getImageData(0, 0, sourceWidth, sourceHeight);
        const inspection = inspectInk(imageData, sourceWidth, sourceHeight);
        bounds = {
            left: inspection.left,
            top: inspection.top,
            width: inspection.width,
            height: inspection.height
        };
        inkPixels = inspection.inkPixels;
        makePaperTransparent(imageData);
        sourceContext.putImageData(imageData, 0, 0);
    } catch {
        // A display-only fallback remains usable even if pixel reads are blocked.
    }
    return { sourceCanvas, bounds, inkPixels };
}

export function measureGlyph(image) {
    const frame = createGlyphFrame(image);
    if (!frame) return null;
    return {
        ...frame,
        inkPixels: frame.inkPixels
    };
}

export function drawNormalizedGlyph(canvas, image, options = {}) {
    const paddingRatio = options.paddingRatio ?? DEFAULT_PADDING_RATIO;
    const visualScale = options.visualScale ?? 1;
    const context = canvas.getContext("2d");
    const frame = options.frame ?? createGlyphFrame(image);
    if (!context || !frame) return false;
    const { sourceCanvas, bounds } = frame;

    const usableWidth = canvas.width * (1 - paddingRatio * 2);
    const usableHeight = canvas.height * (1 - paddingRatio * 2);
    const scale = Math.min(usableWidth / bounds.width, usableHeight / bounds.height) * visualScale;
    const drawWidth = bounds.width * scale;
    const drawHeight = bounds.height * scale;
    const targetX = (canvas.width - drawWidth) / 2;
    const targetY = (canvas.height - drawHeight) / 2;

    context.clearRect(0, 0, canvas.width, canvas.height);
    context.imageSmoothingEnabled = true;
    context.imageSmoothingQuality = "high";
    context.drawImage(
        sourceCanvas,
        bounds.left,
        bounds.top,
        bounds.width,
        bounds.height,
        targetX,
        targetY,
        drawWidth,
        drawHeight
    );
    return true;
}

function loadImage(url, crossOrigin) {
    return new Promise((resolve, reject) => {
        const image = new Image();
        if (crossOrigin) image.crossOrigin = "anonymous";
        image.onload = () => resolve(image);
        image.onerror = () => reject(new Error("字图加载失败"));
        image.src = url;
    });
}

export async function loadGlyphImage(url) {
    try {
        return await loadImage(url, true);
    } catch {
        // Some browser cache or local security settings can reject a CORS image
        // even though the normal image request is available. Retry as a display-only image.
        return loadImage(url, false);
    }
}
