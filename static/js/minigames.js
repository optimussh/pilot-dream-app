let currentGameId = null;
    let gameInterval = null;
    let gameState = {};

    async function loadStats() {
        try {
            if (!document.getElementById('stat-played')) return;
            const res = await fetch('/api/minigames/stats');
            const data = await res.json();
            document.getElementById('stat-played').innerText = data.played_count;
            document.getElementById('stat-wins').innerText = data.wins;
            document.getElementById('stat-rewards').innerText = data.rewards.toLocaleString() + '원';
        } catch (e) {
            console.error(e);
        }
    }

    async function submitScore(score, isWin) {
        if (!currentGameId) return;
        try {
            const res = await fetch('/api/minigames/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ game_id: currentGameId, score, is_win: isWin })
            });
            const data = await res.json();
            if (data.status === 'ok') {
                if (window.updateWalletDisplay && data.wallet) {
                    window.updateWalletDisplay(data.wallet.balance, data.wallet.balance_formatted);
                }
                loadStats();
                if (typeof window.onMinigameResult === 'function') {
                    window.onMinigameResult({ gameId: currentGameId, isWin, score, data });
                }
                if (isWin) {
                    confetti({
                        particleCount: 100,
                        spread: 70,
                        origin: { y: 0.6 }
                    });
                    const rewardAmount = data.reward || 0;
                    if (window.showLearningReward) {
                        window.showLearningReward({
                            amount: rewardAmount,
                            balance: data.wallet.balance,
                            title: `미니게임 우승! 🥳`,
                            subtitle: data.message
                        });
                    } else {
                        alert(`우승했어요! ${rewardAmount.toLocaleString()}원을 벌었습니다!`);
                    }
                } else {
                    alert('아쉽네요! 다음엔 꼭 성공할 수 있을 거예요!');
                }
            }
        } catch (e) {
            console.error(e);
        }
    }

    function startGame(gameId) {
        currentGameId = gameId;
        const titles = {
            'luggage': '🧳 수하물 무게 맞추기',
            'refuel': '⛽ 급유 스탑 챌린지',
            'landing': '🛬 활주로 정렬 착륙'
        };
        document.getElementById('modal-title').innerText = titles[gameId];
        document.getElementById('game-modal').classList.remove('hidden');
        document.getElementById('game-modal').classList.add('flex');
        
        resetGameUI();
    }

    function closeGame() {
        if (gameInterval) {
            clearInterval(gameInterval);
            gameInterval = null;
        }
        document.getElementById('game-modal').classList.add('hidden');
        document.getElementById('game-modal').classList.remove('flex');
        currentGameId = null;
    }

    function resetGameUI() {
        if (gameInterval) clearInterval(gameInterval);
        const container = document.getElementById('game-container');
        const footer = document.getElementById('game-footer');
        
        container.innerHTML = `<div class="text-white text-center"><div class="text-4xl mb-4">🎮</div><div class="text-lg">준비가 되면 시작 버튼을 누르세요!</div></div>`;
        footer.innerHTML = `<button onclick="initCurrentGame()" class="w-full py-3 bg-[#33ff33] text-black rounded-xl font-bold text-lg hover:bg-[#22cc22]">게임 시작!</button>`;
    }

    function initCurrentGame() {
        const container = document.getElementById('game-container');
        const footer = document.getElementById('game-footer');
        container.innerHTML = '';
        footer.innerHTML = '';
        
        if (currentGameId === 'luggage') initLuggageGame(container, footer);
        else if (currentGameId === 'refuel') initRefuelGame(container, footer);
        else if (currentGameId === 'landing') initLandingGame(container, footer);
    }

    // --- GAME 1: Luggage ---
    function initLuggageGame(container, footer) {
        gameState = { left: 10, right: 90, timeLeft: 15, playing: true };
        
        container.innerHTML = `
            <div class="absolute top-4 text-xl font-bold text-white flex gap-2">
                ⏱️ <span id="luggage-time">15</span>초
            </div>
            <div class="w-full h-8 bg-white/10 rounded-full mt-10 relative overflow-hidden flex">
                <div id="bar-left" class="h-full bg-blue-500 transition-all duration-200" style="width: 10%;"></div>
                <div id="bar-right" class="h-full bg-red-500 transition-all duration-200" style="width: 90%;"></div>
                <div class="absolute left-0 top-0 w-full h-full pointer-events-none flex" style="background: transparent;">
                    <div class="h-full" style="width: 45%;"></div>
                    <div class="h-full bg-[#33ff33]/40 border-x-2 border-[#33ff33]" style="width: 10%;"></div>
                </div>
            </div>
            <div class="text-white mt-4 font-bold text-lg text-center" id="luggage-msg">왼쪽 <span class="text-[#33ff33]">45~55%</span>를 맞추세요! (현재 <span id="luggage-val">10</span>%)</div>
            <div class="text-6xl mt-8 transition-transform duration-200" id="plane-tilt">✈️</div>
        `;
        
        footer.innerHTML = `
            <div class="flex gap-4">
                <button onclick="shiftLuggage('left')" class="flex-1 py-4 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-bold text-xl active:scale-95 transition-transform">⬅️ 왼쪽으로 짐 옮기기</button>
                <button onclick="shiftLuggage('right')" class="flex-1 py-4 bg-red-500 hover:bg-red-600 text-white rounded-xl font-bold text-xl active:scale-95 transition-transform">오른쪽으로 짐 옮기기 ➡️</button>
            </div>
        `;

        gameInterval = setInterval(() => {
            if (!gameState.playing) return;
            gameState.timeLeft--;
            document.getElementById('luggage-time').innerText = gameState.timeLeft;
            
            if (gameState.timeLeft <= 0) {
                endLuggageGame();
            }
        }, 1000);
    }
    
    function shiftLuggage(dir) {
        if (!gameState.playing) return;
        const amount = Math.floor(Math.random() * 5) + 3; // 3~7%
        if (dir === 'left') {
            gameState.left += amount;
            if (gameState.left > 100) gameState.left = 100;
        } else {
            gameState.left -= amount;
            if (gameState.left < 0) gameState.left = 0;
        }
        gameState.right = 100 - gameState.left;
        
        document.getElementById('bar-left').style.width = gameState.left + '%';
        document.getElementById('bar-right').style.width = gameState.right + '%';
        document.getElementById('luggage-val').innerText = gameState.left;
        
        const tilt = (gameState.left - 50) * 1.5;
        document.getElementById('plane-tilt').style.transform = `rotate(${-tilt}deg)`;
    }
    
    function endLuggageGame() {
        gameState.playing = false;
        clearInterval(gameInterval);
        const win = gameState.left >= 45 && gameState.left <= 55;
        const score = win ? 100 - Math.abs(50 - gameState.left) * 2 : 0;
        
        document.getElementById('luggage-msg').innerHTML = win ? 
            `<span class="text-[#33ff33] text-2xl">완벽한 균형이에요! 🥳</span>` : 
            `<span class="text-red-500 text-2xl">균형을 잃었어요! 😭</span>`;
            
        setTimeout(() => submitScore(score, win), 1000);
        document.getElementById('game-footer').innerHTML = `<button onclick="resetGameUI()" class="w-full py-3 bg-white/10 text-white rounded-xl font-bold text-lg hover:bg-white/20">다시 하기</button>`;
    }

    // --- GAME 2: Refuel ---
    function initRefuelGame(container, footer) {
        gameState = { fuel: 0, playing: true, speed: 1.5 };
        
        container.innerHTML = `
            <div class="text-white mt-4 font-bold text-lg mb-4">목표: <span class="text-[#33ff33]">80% ~ 90%</span> 사이에서 멈추세요!</div>
            <div class="w-24 h-64 border-4 border-white/20 rounded-xl relative overflow-hidden bg-white/5">
                <!-- Target Zone -->
                <div class="absolute w-full bottom-[80%] h-[10%] bg-[#33ff33]/30 border-y-2 border-[#33ff33] z-10"></div>
                <!-- Fuel -->
                <div id="fuel-bar" class="absolute bottom-0 w-full bg-gradient-to-t from-yellow-600 to-yellow-400" style="height: 0%;"></div>
            </div>
            <div class="text-3xl font-bold text-white mt-4" id="fuel-text">0%</div>
        `;
        
        footer.innerHTML = `
            <button onclick="stopRefuel()" class="w-full py-6 bg-red-500 hover:bg-red-600 text-white rounded-xl font-bold text-2xl shadow-lg shadow-red-500/20 active:scale-95 transition-transform">
                🛑 스탑! (STOP)
            </button>
        `;

        gameInterval = setInterval(() => {
            if (!gameState.playing) return;
            gameState.fuel += gameState.speed;
            if (gameState.fuel > 100) {
                gameState.fuel = 100;
                stopRefuel();
            }
            document.getElementById('fuel-bar').style.height = gameState.fuel + '%';
            document.getElementById('fuel-text').innerText = Math.floor(gameState.fuel) + '%';
        }, 30);
    }
    
    function stopRefuel() {
        if (!gameState.playing) return;
        gameState.playing = false;
        clearInterval(gameInterval);
        
        const win = gameState.fuel >= 80 && gameState.fuel <= 90;
        const score = win ? Math.floor(100 - Math.abs(85 - gameState.fuel)) : 0;
        
        if (win) {
            document.getElementById('fuel-bar').classList.add('bg-[#33ff33]');
            document.getElementById('fuel-text').innerHTML = `<span class="text-[#33ff33]">${Math.floor(gameState.fuel)}% - 완벽해요!</span>`;
        } else {
            document.getElementById('fuel-bar').classList.add('bg-red-500');
            document.getElementById('fuel-text').innerHTML = `<span class="text-red-500">${Math.floor(gameState.fuel)}% - 실패!</span>`;
        }
        
        setTimeout(() => submitScore(score, win), 1000);
        document.getElementById('game-footer').innerHTML = `<button onclick="resetGameUI()" class="w-full py-3 bg-white/10 text-white rounded-xl font-bold text-lg hover:bg-white/20">다시 하기</button>`;
    }

    // --- GAME 3: Landing ---
    function initLandingGame(container, footer) {
        gameState = { pos: 50, timeLeft: 10, playing: true, wind: 0 };
        
        container.innerHTML = `
            <div class="absolute top-4 text-xl font-bold text-white flex gap-2">
                ⏱️ <span id="landing-time">10</span>초
            </div>
            
            <div class="relative w-full h-full flex justify-center items-end pb-10 perspective-[800px] overflow-hidden">
                <!-- Runway -->
                <div class="w-32 h-[200%] bg-gray-800 absolute bottom-0 border-x-4 border-gray-600 rounded-t-lg" style="transform: rotateX(60deg); transform-origin: bottom;">
                    <div class="w-full h-full flex flex-col justify-between items-center py-10 opacity-50">
                        <div class="w-4 h-16 bg-white"></div>
                        <div class="w-4 h-16 bg-white"></div>
                        <div class="w-4 h-16 bg-white"></div>
                        <div class="w-4 h-16 bg-white"></div>
                    </div>
                </div>
                
                <!-- Target Zone Line -->
                <div class="absolute bottom-32 w-16 h-full bg-[#33ff33]/20 border-x border-[#33ff33]"></div>
                
                <!-- Plane -->
                <div id="landing-plane" class="text-6xl absolute bottom-16 transition-all duration-75" style="left: calc(50% - 24px);">🛬</div>
            </div>
            
            <div class="absolute top-16 text-center text-[#ffaa00] font-bold">
                바람: <span id="wind-text">잔잔함</span>
            </div>
        `;
        
        footer.innerHTML = `
            <div class="flex gap-4">
                <button onclick="steerPlane(-10)" class="flex-1 py-4 bg-[#0A84FF] text-white rounded-xl font-bold text-2xl active:scale-95">⬅️</button>
                <button onclick="steerPlane(10)" class="flex-1 py-4 bg-[#0A84FF] text-white rounded-xl font-bold text-2xl active:scale-95">➡️</button>
            </div>
        `;

        gameInterval = setInterval(() => {
            if (!gameState.playing) return;
            
            // Apply wind
            gameState.pos += gameState.wind;
            if (gameState.pos < 10) gameState.pos = 10;
            if (gameState.pos > 90) gameState.pos = 90;
            
            document.getElementById('landing-plane').style.left = `calc(${gameState.pos}% - 24px)`;
            
            // Change wind every second maybe
            if (Math.random() < 0.2) {
                gameState.wind = (Math.random() - 0.5) * 4; // -2 to +2
                const windDir = gameState.wind > 1 ? '오른쪽 ➡️' : (gameState.wind < -1 ? '⬅️ 왼쪽' : '잔잔함');
                document.getElementById('wind-text').innerText = windDir;
            }
        }, 50);

        // Timer
        let timerInt = setInterval(() => {
            if (!gameState.playing) {
                clearInterval(timerInt);
                return;
            }
            gameState.timeLeft--;
            document.getElementById('landing-time').innerText = gameState.timeLeft;
            
            if (gameState.timeLeft <= 0) {
                endLandingGame(timerInt);
            }
        }, 1000);
    }
    
    function steerPlane(amt) {
        if (!gameState.playing) return;
        gameState.pos += amt;
        if (gameState.pos < 10) gameState.pos = 10;
        if (gameState.pos > 90) gameState.pos = 90;
        document.getElementById('landing-plane').style.left = `calc(${gameState.pos}% - 24px)`;
    }
    
    function endLandingGame(timerInt) {
        gameState.playing = false;
        clearInterval(gameInterval);
        clearInterval(timerInt);
        
        const win = gameState.pos >= 40 && gameState.pos <= 60;
        const score = win ? 100 - Math.abs(50 - gameState.pos) * 2 : 0;
        
        const p = document.getElementById('landing-plane');
        if (win) {
            p.innerHTML = '✨🛬✨';
        } else {
            p.innerHTML = '💥';
            p.classList.add('rotate-45');
        }
        
        setTimeout(() => submitScore(score, win), 1000);
        document.getElementById('game-footer').innerHTML = `<button onclick="resetGameUI()" class="w-full py-3 bg-white/10 text-white rounded-xl font-bold text-lg hover:bg-white/20">다시 하기</button>`;
    }

    // Load stats on page load
    loadStats();
