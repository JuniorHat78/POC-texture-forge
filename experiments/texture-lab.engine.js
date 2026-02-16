(function initTextureLabEngine() {
    const Lab = window.TextureLab;
    if (!Lab || !Lab.dom) {
        return;
    }

    const d = Lab.dom;
    const tileSizeScaleBase = 256;

    function valueNoisePeriodic(x, y, cells, seed) {
        const x0 = Math.floor(x);
        const y0 = Math.floor(y);
        const x1 = x0 + 1;
        const y1 = y0 + 1;

        const fx = Lab.smoothstep(x - x0);
        const fy = Lab.smoothstep(y - y0);

        const n00 = Lab.hash2d(Lab.mod(x0, cells), Lab.mod(y0, cells), seed);
        const n10 = Lab.hash2d(Lab.mod(x1, cells), Lab.mod(y0, cells), seed);
        const n01 = Lab.hash2d(Lab.mod(x0, cells), Lab.mod(y1, cells), seed);
        const n11 = Lab.hash2d(Lab.mod(x1, cells), Lab.mod(y1, cells), seed);

        const nx0 = Lab.lerp(n00, n10, fx);
        const nx1 = Lab.lerp(n01, n11, fx);
        return Lab.lerp(nx0, nx1, fy);
    }

    function fbm(u, v, baseCells, octaves, seed, roughness) {
        const persistence = 0.52 + roughness * 0.2;
        let amplitude = 1;
        let total = 0;
        let normalizer = 0;

        for (let octave = 0; octave < octaves; octave += 1) {
            const frequency = 1 << octave;
            const cells = Math.max(2, Math.floor(baseCells * frequency));
            const sample = valueNoisePeriodic(
                u * cells + octave * 0.57,
                v * cells + octave * 0.41,
                cells,
                seed + octave * 131
            );
            total += sample * amplitude;
            normalizer += amplitude;
            amplitude *= persistence;
        }

        return total / normalizer;
    }

    function toneForStyle(styleKey, base, detail, ridge, u, v, settings) {
        switch (styleKey) {
            case "moss":
                return Lab.clamp(base * 0.75 + ridge * 0.28 + (detail - 0.5) * 0.14, 0, 1);
            case "lava": {
                const glow = Math.pow(base, 1.62);
                const cracks = Math.pow(1 - ridge, 2.25);
                return Lab.clamp(glow + cracks * 0.55, 0, 1);
            }
            case "metal": {
                const bands = Math.abs(Math.sin((u * 1.8 + v * 1.05) * Math.PI * settings.scale));
                return Lab.clamp(base * 0.62 + ridge * 0.14 + bands * 0.28, 0, 1);
            }
            case "sand": {
                const dunes = Math.sin((u * 2.3 - v * 1.4) * Math.PI * settings.scale * 0.45) * 0.09;
                return Lab.clamp(base * 0.82 + ridge * 0.13 + dunes, 0, 1);
            }
            case "ice": {
                const fractures = Math.pow(1 - ridge, 2.8);
                return Lab.clamp(base * 0.58 + (1 - detail) * 0.2 + fractures * 0.4, 0, 1);
            }
            case "toxic": {
                const blobs = Math.pow(ridge, 1.45);
                return Lab.clamp(base * 0.54 + blobs * 0.34 + (detail - 0.5) * 0.22, 0, 1);
            }
            default:
                return base;
        }
    }

    function sampleGradient(styleKey, tone) {
        const stops = Lab.styles[styleKey].stops;
        if (tone <= stops[0].position) {
            return stops[0].color;
        }
        if (tone >= stops[stops.length - 1].position) {
            return stops[stops.length - 1].color;
        }

        for (let i = 1; i < stops.length; i += 1) {
            const previous = stops[i - 1];
            const current = stops[i];
            if (tone <= current.position) {
                const localT = (tone - previous.position) / (current.position - previous.position);
                return {
                    r: Math.round(Lab.lerp(previous.color.r, current.color.r, localT)),
                    g: Math.round(Lab.lerp(previous.color.g, current.color.g, localT)),
                    b: Math.round(Lab.lerp(previous.color.b, current.color.b, localT))
                };
            }
        }

        return stops[stops.length - 1].color;
    }

    function ensureLayerSize(size) {
        const resized = d.textureCanvas.width !== size || d.textureCanvas.height !== size;
        if (!resized) {
            return false;
        }

        d.textureCanvas.width = size;
        d.textureCanvas.height = size;
        Lab.baseCanvas.width = size;
        Lab.baseCanvas.height = size;
        Lab.paintCanvas.width = size;
        Lab.paintCanvas.height = size;
        return true;
    }

    function renderToCanvas(canvas, settings) {
        const context = canvas.getContext("2d", { willReadFrequently: true });
        const width = canvas.width;
        const height = canvas.height;
        const imageData = context.createImageData(width, height);
        const pixels = imageData.data;

        for (let y = 0; y < height; y += 1) {
            const v = y / height;
            for (let x = 0; x < width; x += 1) {
                const u = x / width;

                const base = fbm(u, v, settings.scale, settings.octaves, settings.seed, settings.roughness);
                const detail = fbm(
                    u + 0.217,
                    v + 0.173,
                    settings.scale * 2,
                    Math.max(2, settings.octaves - 1),
                    settings.seed + 991,
                    Lab.clamp(settings.roughness + 0.08, 0, 1.4)
                );
                const ridge = 1 - Math.abs(detail * 2 - 1);

                let tone = toneForStyle(settings.style, base, detail, ridge, u, v, settings);
                tone = (tone - 0.5) * settings.contrast + 0.5;
                tone += (Lab.hash2d(x, y, settings.seed + 4049) - 0.5) * settings.grain;
                tone = Lab.clamp(tone, 0, 1);

                const color = sampleGradient(settings.style, tone);
                const index = (y * width + x) * 4;
                pixels[index] = color.r;
                pixels[index + 1] = color.g;
                pixels[index + 2] = color.b;
                pixels[index + 3] = 255;
            }
        }

        context.putImageData(imageData, 0, 0);
    }

    function drawTiledPreview() {
        const context = d.tileCanvas.getContext("2d");
        context.clearRect(0, 0, d.tileCanvas.width, d.tileCanvas.height);
        const pattern = context.createPattern(d.textureCanvas, "repeat");
        if (!pattern) {
            return;
        }

        context.fillStyle = pattern;
        context.fillRect(0, 0, d.tileCanvas.width, d.tileCanvas.height);

        context.strokeStyle = "rgba(255, 255, 255, 0.24)";
        context.lineWidth = 1;
        context.setLineDash([5, 6]);
        for (let x = 0; x <= d.tileCanvas.width; x += d.tileCanvas.width / 3) {
            context.beginPath();
            context.moveTo(x, 0);
            context.lineTo(x, d.tileCanvas.height);
            context.stroke();
        }
        for (let y = 0; y <= d.tileCanvas.height; y += d.tileCanvas.height / 3) {
            context.beginPath();
            context.moveTo(0, y);
            context.lineTo(d.tileCanvas.width, y);
            context.stroke();
        }
        context.setLineDash([]);
    }

    function composeTextureAndPreview() {
        Lab.contexts.texture.clearRect(0, 0, d.textureCanvas.width, d.textureCanvas.height);
        Lab.contexts.texture.drawImage(Lab.baseCanvas, 0, 0);
        Lab.contexts.texture.drawImage(Lab.paintCanvas, 0, 0);
        drawTiledPreview();
    }

    function renderMain(clearPaint = false) {
        if (Lab.currentMode() === "basic") {
            Lab.applyVariationToAdvanced();
        }

        const settings = Lab.readSettings();
        d.seedInput.value = String(settings.seed);
        const resized = ensureLayerSize(settings.size);
        if (resized || clearPaint) {
            if (typeof Lab.clearPaintLayer === "function") {
                Lab.clearPaintLayer(true);
            } else {
                Lab.contexts.paint.clearRect(0, 0, Lab.paintCanvas.width, Lab.paintCanvas.height);
            }
            Lab.state.handcraftPassCount = 0;
        }

        renderToCanvas(Lab.baseCanvas, settings);
        composeTextureAndPreview();
    }

    function exportTexture() {
        const settings = Lab.readSettings();
        const handcraftTag = Math.round(settings.handcraft * 100);
        const name = `${settings.style}-${settings.seed}-${settings.size}-h${handcraftTag}.png`;
        const link = document.createElement("a");
        link.download = name;
        link.href = d.textureCanvas.toDataURL("image/png");
        link.click();
    }

    Lab.tileSizeScaleBase = tileSizeScaleBase;
    Lab.valueNoisePeriodic = valueNoisePeriodic;
    Lab.fbm = fbm;
    Lab.toneForStyle = toneForStyle;
    Lab.sampleGradient = sampleGradient;
    Lab.ensureLayerSize = ensureLayerSize;
    Lab.renderToCanvas = renderToCanvas;
    Lab.drawTiledPreview = drawTiledPreview;
    Lab.composeTextureAndPreview = composeTextureAndPreview;
    Lab.renderMain = renderMain;
    Lab.exportTexture = exportTexture;
})();
