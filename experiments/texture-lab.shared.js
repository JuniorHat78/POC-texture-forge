(function initTextureLabShared() {
    const Lab = window.TextureLab || (window.TextureLab = {});
    const byId = (id) => document.getElementById(id);

    const dom = {
        controlsPanel: document.querySelector(".controls"),
        textureCanvas: byId("textureCanvas"),
        tileCanvas: byId("tileCanvas"),
        ideasGrid: byId("ideasGrid"),
        modeSelect: byId("modeSelect"),
        styleSelect: byId("styleSelect"),
        seedInput: byId("seedInput"),
        sizeSelect: byId("sizeSelect"),
        variationInput: byId("variationInput"),
        scaleInput: byId("scaleInput"),
        octavesInput: byId("octavesInput"),
        roughnessInput: byId("roughnessInput"),
        contrastInput: byId("contrastInput"),
        grainInput: byId("grainInput"),
        handcraftInput: byId("handcraftInput"),
        brushSizeInput: byId("brushSizeInput"),
        brushOpacityInput: byId("brushOpacityInput"),
        brushModeSelect: byId("brushModeSelect"),
        brushColorInput: byId("brushColorInput"),
        scaleValue: byId("scaleValue"),
        octavesValue: byId("octavesValue"),
        roughnessValue: byId("roughnessValue"),
        contrastValue: byId("contrastValue"),
        grainValue: byId("grainValue"),
        variationValue: byId("variationValue"),
        handcraftValue: byId("handcraftValue"),
        brushSizeValue: byId("brushSizeValue"),
        brushOpacityValue: byId("brushOpacityValue"),
        seedBtn: byId("seedBtn"),
        randomizeBtn: byId("randomizeBtn"),
        renderBtn: byId("renderBtn"),
        exportBtn: byId("exportBtn"),
        ideasBtn: byId("ideasBtn"),
        applyHandcraftBtn: byId("applyHandcraftBtn"),
        clearPaintBtn: byId("clearPaintBtn"),
        undoPaintBtn: byId("undoPaintBtn"),
        redoPaintBtn: byId("redoPaintBtn"),
        renderStatus: byId("renderStatus")
    };

    if (!dom.textureCanvas || !dom.tileCanvas || !dom.controlsPanel) {
        return;
    }

    const baseCanvas = document.createElement("canvas");
    const paintCanvas = document.createElement("canvas");
    const contexts = {
        texture: dom.textureCanvas.getContext("2d"),
        paint: paintCanvas.getContext("2d")
    };
    const state = {
        isPainting: false,
        lastPaintPoint: null,
        handcraftPassCount: 0,
        isRendering: false,
        pendingRenderId: 0,
        pendingRenderSettings: null,
        workerUnavailable: false,
        paintUndoStack: [],
        paintRedoStack: [],
        paintStrokeBefore: null
    };

    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    function lerp(a, b, t) {
        return a + (b - a) * t;
    }

    function smoothstep(t) {
        return t * t * (3 - 2 * t);
    }

    function mod(n, m) {
        return ((n % m) + m) % m;
    }

    function hexToRgb(hex) {
        const clean = hex.replace("#", "");
        const expanded = clean.length === 3
            ? clean.split("").map((ch) => ch + ch).join("")
            : clean;
        const value = parseInt(expanded, 16);
        return {
            r: (value >> 16) & 255,
            g: (value >> 8) & 255,
            b: value & 255
        };
    }

    function rgbToHex(r, g, b) {
        return `#${[r, g, b].map((value) => value.toString(16).padStart(2, "0")).join("")}`;
    }

    function rgbaFromHex(hex, alpha) {
        const color = hexToRgb(hex);
        return `rgba(${color.r}, ${color.g}, ${color.b}, ${alpha.toFixed(3)})`;
    }

    function createRng(seed) {
        let value = (seed >>> 0) || 1;
        return () => {
            value = (Math.imul(value, 1664525) + 1013904223) >>> 0;
            return value / 4294967296;
        };
    }

    function hash2d(x, y, seed) {
        let value = Math.imul(x, 374761393) + Math.imul(y, 668265263) + Math.imul(seed, 1442695041);
        value = (value ^ (value >>> 13)) >>> 0;
        value = Math.imul(value, 1274126177) >>> 0;
        value = (value ^ (value >>> 16)) >>> 0;
        return value / 4294967295;
    }

    const styles = {
        moss: {
            label: "Mossy Stone",
            stops: [
                [0.0, "#101718"],
                [0.22, "#203031"],
                [0.48, "#3b5a46"],
                [0.72, "#6f8d52"],
                [1.0, "#b7cc7b"]
            ]
        },
        lava: {
            label: "Lava Crust",
            stops: [
                [0.0, "#100f14"],
                [0.18, "#2b1a12"],
                [0.42, "#58230f"],
                [0.7, "#b34313"],
                [0.88, "#f59e0b"],
                [1.0, "#fde68a"]
            ]
        },
        metal: {
            label: "Brushed Metal",
            stops: [
                [0.0, "#0f1720"],
                [0.28, "#2c3946"],
                [0.52, "#4c6272"],
                [0.8, "#89a4b5"],
                [1.0, "#d6e3ea"]
            ]
        },
        sand: {
            label: "Dune Sand",
            stops: [
                [0.0, "#1f170f"],
                [0.22, "#5b4122"],
                [0.52, "#ad8550"],
                [0.78, "#e1bc86"],
                [1.0, "#f7e0b8"]
            ]
        },
        ice: {
            label: "Cracked Ice",
            stops: [
                [0.0, "#07131d"],
                [0.18, "#173144"],
                [0.48, "#2f678a"],
                [0.74, "#7cb8d6"],
                [1.0, "#dff5ff"]
            ]
        },
        toxic: {
            label: "Toxic Slime",
            stops: [
                [0.0, "#08120b"],
                [0.22, "#1d3a19"],
                [0.46, "#3e6a1f"],
                [0.72, "#95b91e"],
                [1.0, "#d7f36c"]
            ]
        }
    };

    for (const style of Object.values(styles)) {
        style.stops = style.stops.map(([position, hex]) => ({
            position,
            color: hexToRgb(hex)
        }));
    }

    Lab.dom = dom;
    Lab.baseCanvas = baseCanvas;
    Lab.paintCanvas = paintCanvas;
    Lab.contexts = contexts;
    Lab.state = state;
    Lab.styles = styles;
    Lab.clamp = clamp;
    Lab.lerp = lerp;
    Lab.smoothstep = smoothstep;
    Lab.mod = mod;
    Lab.hexToRgb = hexToRgb;
    Lab.rgbToHex = rgbToHex;
    Lab.rgbaFromHex = rgbaFromHex;
    Lab.createRng = createRng;
    Lab.hash2d = hash2d;
})();
