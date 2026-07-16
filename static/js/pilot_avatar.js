/** 파일럿 아바타 — 남자 실루엣 + 슬롯별 장착 비주얼 (상점·대시보드 공용) */
(function (global) {
    const SLOT_ORDER = ['wings', 'uniform', 'head', 'accessory'];
    const SLOT_LABELS = { head: '머리', uniform: '유니폼', accessory: '악세서리', wings: '윙' };

    const UNIFORM_COLORS = {
        av_uni_student: '#c45c26', av_uni_lcc: '#e85d04', av_uni_fo: '#1e3a5f',
        av_uni_captain: '#0f2744', av_uni_senior: '#1a1a2e', av_uni_ke: '#004B9C',
        av_uni_oz: '#4B0082', av_uni_cargo: '#ea580c', av_uni_winter: '#334155',
        av_uni_summer: '#0ea5e9', av_uni_military: '#365314', av_uni_business: '#1e293b',
        av_uni_retro: '#1d4ed8', av_uni_neon: '#7c3aed', av_uni_space: '#312e81',
        av_uni_legend: '#854d0e', av_uni_trainee: '#b45309', av_uni_instructor: '#111827',
        av_uni_cargo_ke: '#003478', av_uni_hawaiian: '#0d9488',
    };

    const RARITY_GLOW = {
        common: 'rgba(160,160,160,.35)',
        uncommon: 'rgba(51,255,51,.4)',
        rare: 'rgba(10,132,255,.45)',
        epic: 'rgba(168,85,247,.5)',
        legendary: 'rgba(255,170,0,.55)',
    };

    function uniformColor(item) {
        if (!item) return '#1e3a5f';
        if (item.color) return item.color;
        if (UNIFORM_COLORS[item.id]) return UNIFORM_COLORS[item.id];
        const hues = { common: 210, uncommon: 145, rare: 205, epic: 275, legendary: 38 };
        const h = hues[item.rarity] || 210;
        return `hsl(${h}, 48%, 32%)`;
    }

    function accessoryZone(item) {
        const e = item?.emoji || '';
        if (/🕶️|🎧|⛑️|👑|🧢|🎩/.test(e)) return 'face';
        if (/⌚|🧤/.test(e)) return 'hand';
        if (/💼|🗺️|📱|🔦/.test(e)) return 'side';
        return 'chest';
    }

    function buildBaseFigure() {
        return `<svg class="pa-base-svg" viewBox="0 0 100 160" aria-hidden="true">
            <ellipse cx="50" cy="152" rx="22" ry="5" fill="rgba(0,0,0,.25)"/>
            <rect x="36" y="118" width="10" height="32" rx="4" fill="#1a1a22"/>
            <rect x="54" y="118" width="10" height="32" rx="4" fill="#1a1a22"/>
            <rect x="34" y="146" width="14" height="6" rx="2" fill="#0a0a0a"/>
            <rect x="52" y="146" width="14" height="6" rx="2" fill="#0a0a0a"/>
            <path d="M28 72 Q22 90 26 108 L34 108 Q30 90 34 74 Z" fill="#e8b896"/>
            <path d="M72 72 Q78 90 74 108 L66 108 Q70 90 66 74 Z" fill="#e8b896"/>
            <rect x="30" y="68" width="40" height="52" rx="10" class="pa-torso-base" fill="#1e3a5f"/>
            <path d="M34 68 L50 62 L66 68 L64 78 L36 78 Z" fill="#152a45"/>
            <circle cx="50" cy="38" r="17" fill="#e8b896"/>
            <path d="M34 30 Q50 18 66 30 Q64 24 50 22 Q36 24 34 30 Z" fill="#2a1810"/>
            <ellipse cx="43" cy="38" rx="2.2" ry="2.8" fill="#1a1a22"/>
            <ellipse cx="57" cy="38" rx="2.2" ry="2.8" fill="#1a1a22"/>
            <path d="M44 44 Q50 48 56 44" stroke="#b45309" stroke-width="1.2" fill="none" stroke-linecap="round"/>
            <rect x="46" y="52" width="8" height="10" rx="3" fill="#e8b896"/>
        </svg>`;
    }

    function layerUniform(item) {
        if (!item) return '';
        const color = uniformColor(item);
        const stripes = (item.id || '').includes('captain') || (item.id || '').includes('senior') ? 4
            : (item.id || '').includes('fo') ? 3 : (item.id || '').includes('student') || (item.id || '').includes('trainee') ? 1 : 2;
        const stripeHtml = Array.from({ length: stripes }, (_, i) =>
            `<span class="pa-stripe" style="background:${i % 2 ? '#ffd700' : '#fff'}"></span>`
        ).join('');
        return `<div class="pa-layer pa-layer-uniform" data-slot="uniform" title="${item.name || ''}">
            <div class="pa-uniform-overlay" style="--pa-uni:${color}">
                <div class="pa-uniform-jacket"></div>
                <div class="pa-epaulettes">${stripeHtml}</div>
                <span class="pa-uniform-emoji">${item.emoji || '👔'}</span>
            </div>
        </div>`;
    }

    function layerHead(item) {
        if (!item) return '';
        return `<div class="pa-layer pa-layer-head" data-slot="head" title="${item.name || ''}">
            <span class="pa-head-item">${item.emoji || '🧢'}</span>
        </div>`;
    }

    function layerWings(item) {
        if (!item) return '';
        const em = item.emoji || '🪽';
        return `<div class="pa-layer pa-layer-wings" data-slot="wings" title="${item.name || ''}">
            <span class="pa-wing left">${em}</span>
            <span class="pa-wing right">${em}</span>
        </div>`;
    }

    function layerAccessory(item) {
        if (!item) return '';
        const zone = accessoryZone(item);
        return `<div class="pa-layer pa-layer-accessory pa-acc-${zone}" data-slot="accessory" title="${item.name || ''}">
            <span class="pa-acc-item">${item.emoji || '⭐'}</span>
        </div>`;
    }

    function layerForSlot(slot, item) {
        if (!item) return '';
        if (slot === 'uniform') return layerUniform(item);
        if (slot === 'head') return layerHead(item);
        if (slot === 'wings') return layerWings(item);
        if (slot === 'accessory') return layerAccessory(item);
        return '';
    }

    function resolveEquipped(equipped) {
        const slots = {};
        if (!equipped) return slots;
        if (equipped.head || equipped.uniform) {
            SLOT_ORDER.forEach(s => { if (equipped[s]) slots[s] = equipped[s]; });
            return slots;
        }
        Object.entries(equipped).forEach(([slot, val]) => {
            if (val && typeof val === 'object') slots[slot] = val;
        });
        return slots;
    }

    function buildPreviewHtml(equipped, opts) {
        const slots = resolveEquipped(equipped);
        const size = opts?.size === 'sm' ? 'pa-sm' : opts?.size === 'xs' ? 'pa-xs' : 'pa-lg';
        const interactive = opts?.interactive ? 'pa-interactive' : '';
        const highlight = opts?.highlightSlot ? `pa-highlight-${opts.highlightSlot}` : '';
        const layers = SLOT_ORDER.map(s => layerForSlot(s, slots[s])).join('');
        const hotspots = opts?.interactive ? SLOT_ORDER.map(s => `
            <button type="button" class="pa-hotspot pa-hotspot-${s}" data-slot="${s}" title="${SLOT_LABELS[s]}">
                <span class="pa-hotspot-dot"></span>
                <span class="pa-hotspot-label">${SLOT_LABELS[s]}</span>
            </button>`).join('') : '';
        return `<div class="pilot-avatar ${size} ${interactive} ${highlight}" data-pa-root>
            <div class="pa-stage">
                ${buildBaseFigure()}
                <div class="pa-layers">${layers}</div>
                ${hotspots}
            </div>
        </div>`;
    }

    function mount(container, equipped, opts) {
        if (!container) return;
        const html = buildPreviewHtml(equipped, opts);
        container.innerHTML = html;
        applyTorsoTint(container, equipped);
    }

    function applyTorsoTint(container, equipped) {
        const slots = resolveEquipped(equipped);
        const torso = container.querySelector('.pa-torso-base');
        if (torso && slots.uniform) torso.setAttribute('fill', uniformColor(slots.uniform));
    }

    function update(container, equipped, opts) {
        mount(container, equipped, opts);
    }

    function slotAnchor(container, slot) {
        const layer = container.querySelector(`[data-slot="${slot}"]`) ||
            container.querySelector(`.pa-hotspot-${slot}`) ||
            container.querySelector('.pa-stage');
        return layer || container;
    }

    function playEquipFly(sourceEl, targetContainer, slot, emoji, onDone) {
        if (!sourceEl || !targetContainer) { if (onDone) onDone(); return; }
        const stage = targetContainer.querySelector('.pa-stage') || targetContainer;
        const target = slotAnchor(targetContainer, slot);
        const stageRect = stage.getBoundingClientRect();
        const srcRect = sourceEl.getBoundingClientRect();
        const tgtRect = target.getBoundingClientRect();
        const ghost = document.createElement('div');
        ghost.className = 'pa-fly-ghost';
        ghost.textContent = emoji || '✨';
        document.body.appendChild(ghost);
        const startX = srcRect.left + srcRect.width / 2;
        const startY = srcRect.top + srcRect.height / 2;
        const endX = tgtRect.left + tgtRect.width / 2;
        const endY = tgtRect.top + tgtRect.height / 2;
        ghost.style.left = startX + 'px';
        ghost.style.top = startY + 'px';
        requestAnimationFrame(() => {
            ghost.classList.add('pa-fly-active');
            ghost.style.left = endX + 'px';
            ghost.style.top = endY + 'px';
            ghost.style.transform = 'translate(-50%,-50%) scale(0.85)';
        });
        const layer = targetContainer.querySelector(`[data-slot="${slot}"]`);
        if (layer) layer.classList.add('pa-slot-pop');
        setTimeout(() => {
            ghost.remove();
            if (layer) layer.classList.remove('pa-slot-pop');
            if (onDone) onDone();
        }, 520);
    }

    function previewCss() {
        return `.pilot-avatar{--pa-skin:#e8b896;position:relative;display:inline-flex;justify-content:center}
.pilot-avatar .pa-stage{position:relative;width:140px;height:200px}
.pilot-avatar.pa-lg .pa-stage{width:180px;height:260px}
.pilot-avatar.pa-sm .pa-stage{width:100px;height:145px}
.pilot-avatar.pa-xs .pa-stage{width:72px;height:105px}
.pa-base-svg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.pa-layers{position:absolute;inset:0;pointer-events:none}
.pa-layer{position:absolute;transition:transform .35s cubic-bezier(.34,1.4,.64,1),opacity .25s}
.pa-layer-uniform{left:8%;right:8%;top:34%;height:38%;display:flex;align-items:center;justify-content:center}
.pa-uniform-overlay{position:relative;width:100%;height:100%;display:flex;align-items:center;justify-content:center}
.pa-uniform-jacket{position:absolute;inset:4% 6%;background:var(--pa-uni,#1e3a5f);border-radius:12px 12px 8px 8px;opacity:.88;box-shadow:inset 0 -8px 16px rgba(0,0,0,.25)}
.pa-epaulettes{position:absolute;top:8%;left:12%;right:12%;display:flex;gap:3px;justify-content:center;z-index:2}
.pa-stripe{width:8px;height:3px;border-radius:2px;box-shadow:0 0 4px rgba(255,215,0,.4)}
.pa-uniform-emoji{position:relative;z-index:3;font-size:1.1rem;filter:drop-shadow(0 2px 4px rgba(0,0,0,.5))}
.pa-layer-head{left:50%;top:2%;transform:translateX(-50%);font-size:2rem;filter:drop-shadow(0 3px 6px rgba(0,0,0,.6))}
.pa-layer-wings{left:0;right:0;top:30%;display:flex;justify-content:space-between;padding:0 2%;font-size:1.35rem}
.pa-wing{filter:drop-shadow(0 2px 5px rgba(0,0,0,.5));animation:pa-wing-float 3s ease-in-out infinite}
.pa-wing.right{animation-delay:.6s}
.pa-layer-accessory{font-size:1.25rem;filter:drop-shadow(0 2px 4px rgba(0,0,0,.5))}
.pa-acc-face{left:54%;top:18%;transform:translateX(-50%)}
.pa-acc-chest{left:50%;top:42%;transform:translateX(-50%)}
.pa-acc-hand{left:78%;top:48%}
.pa-acc-side{left:82%;top:52%;font-size:1.5rem}
.pa-slot-pop{animation:pa-slot-pop .45s cubic-bezier(.34,1.4,.64,1)}
@keyframes pa-slot-pop{0%{transform:scale(.6);opacity:.3}60%{transform:scale(1.12)}100%{transform:scale(1);opacity:1}}
@keyframes pa-wing-float{0%,100%{transform:translateY(0)}50%{transform:translateY(-3px)}}
.pa-fly-ghost{position:fixed;z-index:99999;font-size:2rem;pointer-events:none;transform:translate(-50%,-50%) scale(1.4);transition:left .5s cubic-bezier(.2,.9,.2,1),top .5s cubic-bezier(.2,.9,.2,1),transform .5s ease,opacity .5s;filter:drop-shadow(0 4px 12px rgba(10,132,255,.6))}
.pa-fly-ghost.pa-fly-active{opacity:.95}
.pilot-avatar.pa-interactive .pa-stage{cursor:default}
.pa-hotspot{position:absolute;border:none;background:transparent;cursor:pointer;padding:0;z-index:5}
.pa-hotspot-dot{width:10px;height:10px;border-radius:50%;background:#0A84FF;border:2px solid #fff;display:block;box-shadow:0 0 8px rgba(10,132,255,.6);animation:pa-pulse 2s infinite}
.pa-hotspot-label{position:absolute;left:50%;transform:translateX(-50%);top:-18px;font-size:9px;color:#0A84FF;white-space:nowrap;opacity:0;transition:opacity .2s;background:rgba(0,0,0,.7);padding:2px 6px;border-radius:6px}
.pa-hotspot:hover .pa-hotspot-label,.pa-hotspot.active .pa-hotspot-label{opacity:1}
.pa-hotspot-head{left:50%;top:8%;transform:translateX(-50%)}
.pa-hotspot-uniform{left:50%;top:42%;transform:translateX(-50%)}
.pa-hotspot-wings{left:12%;top:36%}
.pa-hotspot-accessory{left:72%;top:28%}
.pa-highlight-head .pa-layer-head,.pa-highlight-uniform .pa-layer-uniform,.pa-highlight-wings .pa-layer-wings,.pa-highlight-accessory .pa-layer-accessory{outline:2px dashed #0A84FF;outline-offset:4px;border-radius:8px}
@keyframes pa-pulse{0%,100%{box-shadow:0 0 0 0 rgba(10,132,255,.5)}50%{box-shadow:0 0 0 6px rgba(10,132,255,0)}}
.pilot-avatar.pa-sm .pa-layer-head{font-size:1.4rem}
.pilot-avatar.pa-sm .pa-layer-wings{font-size:1rem}
.pilot-avatar.pa-xs .pa-layer-head{font-size:1rem}
.pilot-avatar.pa-xs .pa-layer-wings{font-size:.75rem}
.avatar-stage-card{background:linear-gradient(180deg,#0d1520 0%,#0a0a0c 100%);border:1px solid #2c2c2e;border-radius:20px;padding:16px;display:flex;flex-direction:column;align-items:center}
.avatar-modal-slot.active{border-color:#0A84FF!important;color:#0A84FF}`;
    }

    global.PilotAvatar = {
        SLOT_ORDER,
        SLOT_LABELS,
        buildPreviewHtml,
        mount,
        update,
        playEquipFly,
        previewCss,
        resolveEquipped,
        uniformColor,
    };
})(typeof window !== 'undefined' ? window : globalThis);