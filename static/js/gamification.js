async function trackActivity(type, detail = '') {
    try {
        await fetch('/api/gamification/activity', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type, detail })
        });
    } catch (e) { /* silent */ }
}

function formatKRW(amount) {
    return '₩' + Number(amount || 0).toLocaleString();
}

function updateWalletDisplay(balance, formatted) {
    const text = formatted || formatKRW(balance);
    ['nav-wallet', 'ls-wallet', 'dash-wallet'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    });
}

async function refreshWalletFromServer() {
    try {
        const res = await fetch('/api/gamification/status');
        const data = await res.json();
        if (data.wallet) {
            updateWalletDisplay(data.wallet.balance, data.wallet.balance_formatted);
        }
        return data;
    } catch (e) {
        return null;
    }
}

const LEARNING_UI = {
    quiz: {
        activity: 'quiz',
        title: '오늘의 퀴즈 완료!',
        tomorrow: '내일 새로운 5문제가 열립니다',
        extraTitle: '추가 학습 완료!',
        moreLabel: '학습 더하기',
        moreHint: '새 문제 5개 · 보상 50%',
        bannerId: 'daily-done-banner',
        titleId: 'quiz-banner-title',
        descId: 'quiz-banner-desc',
        actionsId: 'quiz-actions',
        extraBannerId: 'extra-banner',
    },
    flashcard: {
        activity: 'flashcard',
        title: '오늘의 학습 완료!',
        tomorrow: '내일 새로운 5장이 열립니다',
        extraTitle: '추가 학습 완료!',
        moreLabel: '학습 더하기',
        moreHint: '새 카드 5장 · 보상 50%',
        bannerId: 'fc-done-banner',
        titleId: 'fc-banner-title',
        descId: 'fc-banner-desc',
        actionsId: 'fc-actions',
        extraBannerId: 'fc-extra-banner',
    },
    scenarios: {
        activity: 'scenarios',
        title: '오늘의 비상 훈련 완료!',
        tomorrow: '내일 새로운 4개 훈련이 열립니다',
        extraTitle: '추가 훈련 완료!',
        moreLabel: '학습 더하기',
        moreHint: '새 시나리오 4개 · 보상 50%',
        bannerId: 'daily-done-banner',
        titleId: 'sc-banner-title',
        descId: 'sc-banner-desc',
        actionsId: 'sc-actions',
        extraBannerId: 'extra-banner',
    },
};

function ensureRewardModal() {
    if (document.getElementById('learning-reward-modal')) return;
    const modal = document.createElement('div');
    modal.id = 'learning-reward-modal';
    modal.className = 'hidden fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4';
    modal.innerHTML = `
        <div class="info-card p-8 rounded-2xl max-w-sm w-full text-center border border-[#ffaa00]/50 shadow-2xl">
            <div class="text-5xl mb-3" id="lr-emoji">💰</div>
            <div class="font-bold text-xl mb-1" id="lr-title">보상 지급 완료!</div>
            <div class="text-sm text-gray-400 mb-4" id="lr-subtitle"></div>
            <div class="text-3xl font-bold text-[#ffaa00] mb-2" id="lr-amount">+₩0</div>
            <div class="text-xs text-gray-500 mb-4">지갑 잔액: <span id="lr-balance" class="text-[#33ff33] font-semibold">₩0</span></div>
            <div id="lr-bonuses" class="text-xs text-[#0A84FF] mb-4 hidden"></div>
            <button type="button" onclick="closeLearningReward()" class="w-full py-3 bg-[#ffaa00] text-black font-bold rounded-xl hover:opacity-90">확인</button>
        </div>`;
    document.body.appendChild(modal);
    modal.addEventListener('click', e => {
        if (e.target === modal) closeLearningReward();
    });
}

let _rewardOnClose = null;

function showLearningReward(opts = {}) {
    ensureRewardModal();
    const modal = document.getElementById('learning-reward-modal');
    document.getElementById('lr-emoji').textContent = opts.emoji || '💰';
    document.getElementById('lr-title').textContent = opts.title || '보상 지급 완료!';
    document.getElementById('lr-subtitle').textContent = opts.subtitle || '지갑에 입금되었습니다.';
    document.getElementById('lr-amount').textContent = '+' + formatKRW(opts.amount || 0);
    document.getElementById('lr-balance').textContent = formatKRW(opts.balance || 0);

    const bonusEl = document.getElementById('lr-bonuses');
    if (opts.bonuses && opts.bonuses.length) {
        bonusEl.classList.remove('hidden');
        bonusEl.innerHTML = opts.bonuses.map(b =>
            `<div>${b.icon || '🎁'} ${b.title}: +${b.amount_formatted || formatKRW(b.amount)}</div>`
        ).join('');
    } else {
        bonusEl.classList.add('hidden');
        bonusEl.innerHTML = '';
    }

    _rewardOnClose = opts.onClose || null;
    modal.classList.remove('hidden');
}

function closeLearningReward() {
    const modal = document.getElementById('learning-reward-modal');
    if (modal) modal.classList.add('hidden');
    if (_rewardOnClose) {
        const fn = _rewardOnClose;
        _rewardOnClose = null;
        fn();
    }
}

let _lastLearningReward = null;

function storeLearningReward(data) {
    if (!data) return;
    const amount = data.session_money || data.money_earned;
    if (amount || data.wallet_balance != null) {
        _lastLearningReward = { ...data, money_earned: amount || data.money_earned };
    }
}

function claimStoredReward(opts = {}) {
    const reward = _lastLearningReward;
    const amount = reward?.money_earned || reward?.session_money || 0;
    if (amount > 0) {
        if (reward.wallet_balance != null) {
            updateWalletDisplay(reward.wallet_balance);
        } else {
            refreshWalletFromServer();
        }
        const noteId = opts.noteId;
        if (noteId) {
            const note = document.getElementById(noteId);
            if (note) {
                note.classList.remove('hidden');
                note.innerHTML = `💰 보상 <b class="text-[#ffaa00]">+${formatKRW(amount)}</b> 지갑에 입금됐어요!`;
            }
            return;
        }
        if (opts.showPopup === false) {
            return;
        }
        handleLearningReward(reward, {
            title: opts.title || '보상 확인',
            subtitle: opts.subtitle || '지갑에 입금된 보상입니다.',
            emoji: opts.emoji || '💰',
            showPopup: true,
        });
        return;
    }
    refreshWalletFromServer().then(d => {
        const bal = d?.wallet?.balance_formatted || '₩0';
        alert('보상은 이미 지갑에 입금되었습니다.\n현재 잔액: ' + bal);
    });
}

function renderLearningActions(containerId, data, activityType) {
    const el = document.getElementById(containerId);
    if (!el) return;

    const isExtraMode = data.mode === 'extra' || data.extra_active;
    const showBar = (data.daily_done && !isExtraMode) || data.extra_done;
    if (!showBar) {
        el.classList.add('hidden');
        el.innerHTML = '';
        return;
    }

    const cfg = Object.values(LEARNING_UI).find(c => c.activity === activityType) || {};
    const canExtra = data.can_extra && !data.extra_done;
    el.classList.remove('hidden');
    const noteId = `${cfg.actionsId}-note`;
    const rewardAmt = data.money_earned || data.session_money || 0;
    el.innerHTML = `
        <div class="flex flex-col sm:flex-row gap-3 w-full">
            <button type="button" onclick="claimStoredReward({ title: '보상 확인', emoji: '💰', noteId: '${noteId}', showPopup: false })"
                class="flex-1 py-3 bg-[#ffaa00] text-black font-bold rounded-xl">보상받기${rewardAmt ? ` (+${formatKRW(rewardAmt)})` : ''}</button>
            ${canExtra ? `
            <button type="button" onclick="startExtraLearning('${activityType}')"
                class="flex-1 py-3 bg-[#0A84FF] text-white font-bold rounded-xl">${cfg.moreLabel || '학습 더하기'}</button>` : ''}
        </div>
        <p id="${noteId}" class="hidden text-xs text-[#33ff33] mt-2 w-full"></p>
        ${canExtra
            ? `<p class="text-[10px] text-gray-500 mt-2 w-full">${cfg.moreHint || '한번 더 학습 · 보상 50%'}</p>`
            : `<p class="text-[10px] text-gray-500 mt-2 w-full">내일 새 학습이 열립니다</p>`}
    `;
}

function applyLearningCompleteUI(pageKey, data) {
    const cfg = LEARNING_UI[pageKey];
    if (!cfg) return;

    const banner = document.getElementById(cfg.bannerId);
    const extraBanner = cfg.extraBannerId ? document.getElementById(cfg.extraBannerId) : null;
    if (extraBanner) extraBanner.classList.add('hidden');
    if (banner) banner.classList.remove('hidden');

    const titleEl = document.getElementById(cfg.titleId);
    const descEl = document.getElementById(cfg.descId);
    if (data.extra_done) {
        if (titleEl) titleEl.textContent = cfg.extraTitle;
        if (descEl) descEl.textContent = '내일 새 학습이 열립니다';
    } else {
        if (titleEl) titleEl.textContent = cfg.title;
        if (descEl) descEl.textContent = cfg.tomorrow;
    }

    const uiData = { ...data, daily_done: true };
    renderLearningActions(cfg.actionsId, uiData, cfg.activity);
}

function showLearningExtraMode(pageKey) {
    const cfg = LEARNING_UI[pageKey];
    if (!cfg) return;
    const banner = document.getElementById(cfg.bannerId);
    const extraBanner = document.getElementById(cfg.extraBannerId);
    if (banner) banner.classList.add('hidden');
    if (extraBanner) extraBanner.classList.remove('hidden');
}

let _learningPageReload = null;

function setLearningPageReload(fn) {
    _learningPageReload = fn;
}

async function startExtraLearning(activityType, reloadFn) {
    const paths = { quiz: 'quiz', flashcard: 'flashcard', scenarios: 'scenarios' };
    const path = paths[activityType] || activityType;
    const res = await fetch(`/api/gamification/${path}/extra`, { method: 'POST' });
    const data = await res.json();
    if (data.error) {
        alert(data.error);
        return;
    }
    const reload = reloadFn || _learningPageReload;
    if (typeof reload === 'function') reload();
}

function finishLearningSession(pageKey, data, opts = {}) {
    const rewardData = { ...data };
    if (data.daily_done && data.session_money) {
        rewardData.money_earned = data.session_money;
    }
    storeLearningReward(rewardData);
    if (data.wallet_balance != null) {
        updateWalletDisplay(data.wallet_balance);
    }

    const isExtraDone = data.extra_done || (data.mode === 'extra' && data.daily_done);
    const isDailyComplete = data.daily_done && data.mode !== 'extra';
    const showPopup = opts.showPopup ?? isExtraDone;

    if (isDailyComplete || isExtraDone) {
        if (isExtraDone) data.extra_done = true;
        applyLearningCompleteUI(pageKey, data);
    }

    if (showPopup && rewardData.money_earned) {
        handleLearningReward(rewardData, {
            title: opts.rewardTitle || (isExtraDone ? '추가 학습 보상!' : '학습 보상!'),
            subtitle: opts.rewardSubtitle || '지갑에 입금되었습니다.',
            emoji: opts.emoji || '💰',
            bonuses: data.bonuses,
            onClose: opts.onClose,
            showPopup: true,
        });
    } else if (opts.onClose) {
        opts.onClose();
    }
}

function handleLearningReward(data, opts = {}) {
    if (opts.showPopup !== false) {
        storeLearningReward(data);
    }
    const money = data.money_earned || 0;
    if (data.wallet_balance != null) {
        updateWalletDisplay(data.wallet_balance);
    } else {
        refreshWalletFromServer();
    }
    if (money > 0 && opts.showPopup !== false) {
        showLearningReward({
            amount: money,
            balance: data.wallet_balance,
            title: opts.title || '보상 지급 완료!',
            subtitle: opts.subtitle || '지갑에 자동으로 입금되었습니다.',
            emoji: opts.emoji,
            bonuses: data.bonuses,
            onClose: opts.onClose
        });
        return true;
    }
    if (opts.onClose) opts.onClose();
    return false;
}

document.addEventListener('DOMContentLoaded', () => {
    refreshWalletFromServer();
});