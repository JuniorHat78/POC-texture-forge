(function initTextureLabWorker() {
    const styleStops = {
        moss: [
            [0.0, "#101718"],
            [0.22, "#203031"],
            [0.48, "#3b5a46"],
            [0.72, "#6f8d52"],
            [1.0, "#b7cc7b"]
        ],
        lava: [
            [0.0, "#100f14"],
            [0.18, "#2b1a12"],
            [0.42, "#58230f"],
            [0.7, "#b34313"],
            [0.88, "#f59e0b"],
            [1.0, "#fde68a"]
        ],
        metal: [
            [0.0, "#0f1720"],
            [0.28, "#2c3946"],
            [0.52, "#4c6272"],
            [0.8, "#89a4b5"],
            [1.0, "#d6e3ea"]
        ],
        sand: [
            [0.0, "#1f170f"],
            [0.22, "#5b4122"],
            [0.52, "#ad8550"],
            [0.78, "#e1bc86"],
            [1.0, "#f7e0b8"]
        ],
        ice: [
            [0.0, "#07131d"],
            [0.18, "#173144"],
            [0.48, "#2f678a"],
            [0.74, "#7cb8d6"],
            [1.0, "#dff5ff"]
        ],
        toxic: [
            [0.0, "#08120b"],
            [0.22, "#1d3a19"],
            [0.46, "#3e6a1f"],
            [0.72, "#95b91e"],
            [1.0, "#d7f36c"]
        ]
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
            ? clean.split("").map((char) => char + char).join("")
            : clean;
        const value = parseInt(expanded, 16);
        return {
            r: (value >> 16) & 255,
            g: (value >> 8) & 255,
            b: value & 255
        };
    }

    function hash2d(x, y, seed) {
        let value = Math.imul(x, 374761393) + Math.imul(y, 668265263) + Math.imul(seed, 1442695041);
        value = (value ^ (value >>> 13)) >>> 0;
        value = Math.imul(value, 1274126177) >>> 0;
        value = (value ^ (value >>> 16)) >>> 0;
        return value / 4294967295;
    }

    function valueNoisePeriodic(x, y, cells, seed) {
        const x0 = Math.floor(x);
        const y0 = Math.floor(y);
        const x1 = x0 + 1;
        const y1 = y0 + 1;

        const fx = smoothstep(x - x0);
        const fy = smoothstep(y - y0);

        const n00 = hash2d(mod(x0, cells), mod(y0, cells), seed);
        const n10 = hash2d(mod(x1, cells), mod(y0, cells), seed);
        const n01 = hash2d(mod(x0, cells), mod(y1, cells), seed);
        const n11 = hash2d(mod(x1, cells), mod(y1, cells), seed);

        const nx0 = lerp(n00, n10, fx);
        const nx1 = lerp(n01, n11, fx);
        return lerp(nx0, nx1, fy);
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
                return clamp(base * 0.75 + ridge * 0.28 + (detail - 0.5) * 0.14, 0, 1);
            case "lava": {
                const glow = Math.pow(base, 1.62);
                const cracks = Math.pow(1 - ridge, 2.25);
                return clamp(glow + cracks * 0.55, 0, 1);
            }
            case "metal": {
                const bands = Math.abs(Math.sin((u * 1.8 + v * 1.05) * Math.PI * settings.scale));
                return clamp(base * 0.62 + ridge * 0.14 + bands * 0.28, 0, 1);
            }
            case "sand": {
                const dunes = Math.sin((u * 2.3 - v * 1.4) * Math.PI * settings.scale * 0.45) * 0.09;
                return clamp(base * 0.82 + ridge * 0.13 + dunes, 0, 1);
            }
            case "ice": {
                const fractures = Math.pow(1 - ridge, 2.8);
                return clamp(base * 0.58 + (1 - detail) * 0.2 + fractures * 0.4, 0, 1);
            }
            case "toxic": {
                const blobs = Math.pow(ridge, 1.45);
                return clamp(base * 0.54 + blobs * 0.34 + (detail - 0.5) * 0.22, 0, 1);
            }
            default:
                return base;
        }
    }

    function normalizedStops(styleKey) {
        const raw = styleStops[styleKey] || styleStops.moss;
        return raw.map(([position, hex]) => ({
            position,
            color: hexToRgb(hex)
        }));
    }

    function sampleGradient(stops, tone) {
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
                    r: Math.round(lerp(previous.color.r, current.color.r, localT)),
                    g: Math.round(lerp(previous.color.g, current.color.g, localT)),
                    b: Math.round(lerp(previous.color.b, current.color.b, localT))
                };
            }
        }

        return stops[stops.length - 1].color;
    }

    function sanitizeSettings(input) {
        const fallback = {
            style: "moss",
            seed: 1,
            size: 256,
            scale: 7,
            octaves: 4,
            roughness: 0.72,
            contrast: 1.18,
            grain: 0.08
        };
        const settings = Object.assign({}, fallback, input || {});
        settings.style = String(settings.style || "moss").toLowerCase();
        if (!styleStops[settings.style]) {
            settings.style = "moss";
        }
        settings.seed = Math.max(1, Math.floor(Number(settings.seed) || 1));
        settings.size = Math.max(32, Math.floor(Number(settings.size) || 256));
        settings.scale = clamp(Math.floor(Number(settings.scale) || 7), 2, 32);
        settings.octaves = clamp(Math.floor(Number(settings.octaves) || 4), 1, 8);
        settings.roughness = clamp(Number(settings.roughness) || 0.72, 0, 1.5);
        settings.contrast = clamp(Number(settings.contrast) || 1.18, 0.4, 3.0);
        settings.grain = clamp(Number(settings.grain) || 0.08, 0, 0.6);
        return settings;
    }

    function renderTexture(settings) {
        const width = settings.size;
        const height = settings.size;
        const pixels = new Uint8ClampedArray(width * height * 4);
        const stops = normalizedStops(settings.style);

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
                    clamp(settings.roughness + 0.08, 0, 1.4)
                );
                const ridge = 1 - Math.abs(detail * 2 - 1);
                let tone = toneForStyle(settings.style, base, detail, ridge, u, v, settings);
                tone = (tone - 0.5) * settings.contrast + 0.5;
                tone += (hash2d(x, y, settings.seed + 4049) - 0.5) * settings.grain;
                tone = clamp(tone, 0, 1);
                const color = sampleGradient(stops, tone);

                const idx = (y * width + x) * 4;
                pixels[idx] = color.r;
                pixels[idx + 1] = color.g;
                pixels[idx + 2] = color.b;
                pixels[idx + 3] = 255;
            }
        }

        return {
            width,
            height,
            pixels
        };
    }

    self.addEventListener("message", (event) => {
        const payload = event.data || {};
        if (payload.type !== "render") {
            return;
        }

        try {
            const settings = sanitizeSettings(payload.settings);
            const rendered = renderTexture(settings);
            self.postMessage(
                {
                    type: "rendered",
                    requestId: payload.requestId,
                    width: rendered.width,
                    height: rendered.height,
                    pixels: rendered.pixels
                },
                [rendered.pixels.buffer]
            );
        } catch {
            self.postMessage({
                type: "render-failed",
                requestId: payload.requestId
            });
        }
    });
})();
