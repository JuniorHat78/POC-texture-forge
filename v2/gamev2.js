const canvas = document.getElementById("canvas");
const context = canvas.getContext("2d");
const scoreEl = document.getElementById("score");
const bestEl = document.getElementById("best");
const overlayEl = document.getElementById("overlay");
const startBtn = document.getElementById("startBtn");
const pauseBtn = document.getElementById("pauseBtn");
const restartBtn = document.getElementById("restartBtn");

const tileSize = 20;
const cols = canvas.width / tileSize;
const rows = canvas.height / tileSize;

const baseSpeedMs = 110;
const minSpeedMs = 60;
const maxQueuedTurns = 3;
const deathAnimationDurationMs = 900;
const OPPOSITE = {
    up: "down",
    down: "up",
    left: "right",
    right: "left"
};

let snake;
let direction;
let directionQueue;
let food;
let score;
let bestScore = loadBestScore();
let tickMs;
let gameTimer = null;
let started = false;
let paused = true;
let gameOver = false;
let deathHead = null;
let deathAnimationFrame = null;

const keyToDirection = {
    ArrowUp: "up",
    ArrowDown: "down",
    ArrowLeft: "left",
    ArrowRight: "right",
    w: "up",
    W: "up",
    s: "down",
    S: "down",
    a: "left",
    A: "left",
    d: "right",
    D: "right"
};

bestEl.textContent = String(bestScore);

function loadBestScore() {
    try {
        const raw = localStorage.getItem("snake-v2-best-score");
        const parsed = Number(raw);
        return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
    } catch {
        return 0;
    }
}

function saveBestScore(value) {
    try {
        localStorage.setItem("snake-v2-best-score", String(value));
    } catch {
        // Ignore storage failures (private mode, policy restrictions, etc.)
    }
}

function initGameState() {
    const centerX = Math.floor(cols / 2);
    const centerY = Math.floor(rows / 2);

    snake = [
        { x: centerX, y: centerY },
        { x: centerX - 1, y: centerY },
        { x: centerX - 2, y: centerY }
    ];
    direction = "right";
    directionQueue = [];
    score = 0;
    tickMs = baseSpeedMs;
    started = false;
    paused = true;
    gameOver = false;
    deathHead = null;
    stopDeathAnimation();
    food = spawnFood();
    pauseBtn.textContent = "Pause";
    updateScoreUI();
    stopLoop();
    showOverlay("Press Start to play");
    draw();
}

function spawnFood() {
    while (true) {
        const x = Math.floor(Math.random() * cols);
        const y = Math.floor(Math.random() * rows);

        const overlapsSnake = snake.some((part) => part.x === x && part.y === y);
        if (!overlapsSnake) {
            return { x, y };
        }
    }
}

function updateScoreUI() {
    scoreEl.textContent = String(score);
    bestEl.textContent = String(bestScore);
}

function showOverlay(message) {
    overlayEl.textContent = message;
    overlayEl.classList.remove("hidden");
}

function hideOverlay() {
    overlayEl.classList.add("hidden");
}

function stopLoop() {
    if (gameTimer !== null) {
        clearInterval(gameTimer);
        gameTimer = null;
    }
}

function stopDeathAnimation() {
    if (deathAnimationFrame !== null) {
        cancelAnimationFrame(deathAnimationFrame);
        deathAnimationFrame = null;
    }
}

function startLoop() {
    stopLoop();
    gameTimer = setInterval(step, tickMs);
}

function startGame() {
    if (gameOver) {
        initGameState();
    }

    if (!started) {
        started = true;
    }

    paused = false;
    pauseBtn.textContent = "Pause";
    hideOverlay();
    startLoop();
}

function togglePause() {
    if (!started || gameOver) {
        return;
    }

    paused = !paused;
    if (paused) {
        pauseBtn.textContent = "Resume";
        stopLoop();
        showOverlay("Paused");
    } else {
        pauseBtn.textContent = "Pause";
        hideOverlay();
        startLoop();
    }
}

function restartGame() {
    initGameState();
}

function startDeathAnimation(headPosition) {
    gameOver = true;
    paused = true;
    stopLoop();
    stopDeathAnimation();
    deathHead = headPosition;
    hideOverlay();

    const startedAt = performance.now();

    const runFrame = (now) => {
        const elapsed = now - startedAt;
        draw(elapsed);

        if (elapsed < deathAnimationDurationMs) {
            deathAnimationFrame = requestAnimationFrame(runFrame);
        } else {
            deathAnimationFrame = null;
            draw();
            showOverlay("Head cooked - Press Restart");
        }
    };

    deathAnimationFrame = requestAnimationFrame(runFrame);
}

function queueDirection(nextDirection) {
    const previousDirection =
        directionQueue.length > 0 ? directionQueue[directionQueue.length - 1] : direction;

    if (nextDirection === previousDirection) {
        return;
    }

    if (OPPOSITE[previousDirection] === nextDirection) {
        return;
    }

    if (directionQueue.length >= maxQueuedTurns) {
        return;
    }

    directionQueue.push(nextDirection);
}

function applyQueuedDirection() {
    while (directionQueue.length > 0) {
        const candidate = directionQueue.shift();
        if (OPPOSITE[direction] !== candidate) {
            direction = candidate;
            return;
        }
    }
}

function step() {
    if (paused || gameOver) {
        return;
    }

    applyQueuedDirection();

    const newHead = { ...snake[0] };
    if (direction === "up") newHead.y -= 1;
    if (direction === "down") newHead.y += 1;
    if (direction === "left") newHead.x -= 1;
    if (direction === "right") newHead.x += 1;

    const ateFood = newHead.x === food.x && newHead.y === food.y;
    const bodyToCheck = ateFood ? snake : snake.slice(0, -1);
    const hitSelf = bodyToCheck.some((part) => part.x === newHead.x && part.y === newHead.y);
    const hitWall = newHead.x < 0 || newHead.x >= cols || newHead.y < 0 || newHead.y >= rows;

    if (hitSelf || hitWall) {
        const clampedHead = {
            x: Math.max(0, Math.min(cols - 1, newHead.x)),
            y: Math.max(0, Math.min(rows - 1, newHead.y))
        };
        startDeathAnimation(clampedHead);
        return;
    }

    snake.unshift(newHead);

    if (ateFood) {
        score += 1;
        if (score > bestScore) {
            bestScore = score;
            saveBestScore(bestScore);
        }

        food = spawnFood();
        tickMs = Math.max(minSpeedMs, baseSpeedMs - Math.floor(score / 3) * 5);
        startLoop();
    } else {
        snake.pop();
    }

    updateScoreUI();
    draw();
}

function drawGrid() {
    context.strokeStyle = "rgba(148, 163, 184, 0.12)";
    context.lineWidth = 1;

    for (let x = 0; x <= canvas.width; x += tileSize) {
        context.beginPath();
        context.moveTo(x, 0);
        context.lineTo(x, canvas.height);
        context.stroke();
    }

    for (let y = 0; y <= canvas.height; y += tileSize) {
        context.beginPath();
        context.moveTo(0, y);
        context.lineTo(canvas.width, y);
        context.stroke();
    }
}

function drawSnake() {
    snake.forEach((part, index) => {
        context.fillStyle = index === 0 ? "#86efac" : "#22c55e";
        context.fillRect(
            part.x * tileSize + 1,
            part.y * tileSize + 1,
            tileSize - 2,
            tileSize - 2
        );
    });
}

function drawFood() {
    const centerX = food.x * tileSize + tileSize / 2;
    const centerY = food.y * tileSize + tileSize / 2;
    const radius = tileSize * 0.34;

    context.beginPath();
    context.arc(centerX, centerY, radius, 0, Math.PI * 2);
    context.fillStyle = "#ef4444";
    context.fill();
}

function drawDeathEffects(elapsedMs) {
    if (!deathHead) {
        return;
    }

    const progress = Math.min(1, elapsedMs / deathAnimationDurationMs);
    const pulse = Math.sin(progress * Math.PI * 10) * 0.5 + 0.5;
    const headX = deathHead.x * tileSize;
    const headY = deathHead.y * tileSize;
    const centerX = headX + tileSize / 2;
    const centerY = headY + tileSize / 2;

    context.save();

    context.globalAlpha = 0.32 * (1 - progress);
    context.fillStyle = "#fb923c";
    context.beginPath();
    context.arc(centerX, centerY, tileSize * (0.9 + progress * 0.9), 0, Math.PI * 2);
    context.fill();

    context.globalAlpha = 1;
    context.fillStyle = pulse > 0.5 ? "#f97316" : "#dc2626";
    context.fillRect(headX + 1, headY + 1, tileSize - 2, tileSize - 2);

    context.strokeStyle = "#0f172a";
    context.lineWidth = 2;
    context.lineCap = "round";
    const eyeSize = 3.2;
    const leftEyeX = headX + tileSize * 0.33;
    const rightEyeX = headX + tileSize * 0.67;
    const eyeY = headY + tileSize * 0.4;

    context.beginPath();
    context.moveTo(leftEyeX - eyeSize, eyeY - eyeSize);
    context.lineTo(leftEyeX + eyeSize, eyeY + eyeSize);
    context.moveTo(leftEyeX + eyeSize, eyeY - eyeSize);
    context.lineTo(leftEyeX - eyeSize, eyeY + eyeSize);
    context.moveTo(rightEyeX - eyeSize, eyeY - eyeSize);
    context.lineTo(rightEyeX + eyeSize, eyeY + eyeSize);
    context.moveTo(rightEyeX + eyeSize, eyeY - eyeSize);
    context.lineTo(rightEyeX - eyeSize, eyeY + eyeSize);
    context.stroke();

    context.strokeStyle = "#7f1d1d";
    context.lineWidth = 2;
    context.beginPath();
    context.moveTo(headX + tileSize * 0.3, headY + tileSize * 0.7);
    context.lineTo(headX + tileSize * 0.7, headY + tileSize * 0.7);
    context.stroke();

    for (let i = 0; i < 3; i += 1) {
        const life = ((elapsedMs / 180) + i * 0.33) % 1;
        const smokeAlpha = (1 - life) * (1 - progress);
        const smokeX = centerX + Math.sin(elapsedMs / 140 + i * 2) * (3 + i);
        const smokeY = headY - life * 24 - 4;
        const radius = 2.5 + life * 4;

        context.fillStyle = `rgba(203, 213, 225, ${0.35 * smokeAlpha})`;
        context.beginPath();
        context.arc(smokeX, smokeY, radius, 0, Math.PI * 2);
        context.fill();
    }

    context.restore();
}

function draw(deathElapsedMs = null) {
    context.clearRect(0, 0, canvas.width, canvas.height);
    drawGrid();
    drawSnake();
    drawFood();
    if (deathElapsedMs !== null) {
        drawDeathEffects(deathElapsedMs);
    }
}

document.addEventListener("keydown", (event) => {
    const mappedDirection = keyToDirection[event.key];
    if (!mappedDirection) {
        return;
    }

    event.preventDefault();

    if (!started && !gameOver) {
        startGame();
    }

    if (paused && started && !gameOver) {
        togglePause();
    }

    queueDirection(mappedDirection);
});

startBtn.addEventListener("click", startGame);
pauseBtn.addEventListener("click", togglePause);
restartBtn.addEventListener("click", restartGame);

initGameState();
