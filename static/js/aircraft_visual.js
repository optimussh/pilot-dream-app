/** 기종 카테고리별 실루엣·색상 미리보기 (창고·도감·로그북 공용) */
(function (global) {
    const CATEGORY_META = {
        '소형':      { cls: 'cat-small',    label: '소형',   body: '#33ff33', accent: '#1a5c2e', scale: 0.72, shape: 'small' },
        '리저널':    { cls: 'cat-regional', label: '리저널', body: '#4da8da', accent: '#1a4a6e', scale: 0.82, shape: 'regional' },
        '중형':      { cls: 'cat-medium',   label: '중형',   body: '#0A84FF', accent: '#003d80', scale: 1.0,  shape: 'medium' },
        '대형':      { cls: 'cat-large',    label: '대형',   body: '#ffaa00', accent: '#8a5a00', scale: 1.15, shape: 'large' },
        '클래식':    { cls: 'cat-large',    label: '클래식', body: '#ffaa00', accent: '#8a5a00', scale: 1.1,  shape: 'classic' },
        '화물기':    { cls: 'cat-cargo',    label: '화물기', body: '#a78bfa', accent: '#4c1d95', scale: 1.05, shape: 'cargo' },
    };

    const LIVERY_PALETTE = [
        '#004B9C', '#E60012', '#FF6600', '#4B0082', '#00B4B4', '#003087', '#CC0000',
        '#0A84FF', '#33ff33', '#ffaa00', '#a78bfa', '#ec4899', '#14b8a6', '#f97316',
        '#6366f1', '#84cc16', '#06b6d4', '#e11d48', '#7c3aed', '#0891b2', '#ca8a04',
        '#2563eb', '#dc2626', '#059669', '#db2777', '#4f46e5', '#0d9488', '#ea580c',
        '#1d4ed8', '#be123c', '#15803d', '#9333ea', '#0369a1', '#b45309', '#4338ca',
    ];

    const SHAPES = {
        small:    'M10,14 L14,12 L22,11 L68,11 L88,13 L92,14 L88,15 L68,17 L22,17 L14,16 Z M24,11 L27,8 L30,11 M62,11 L65,8 L68,11',
        regional: 'M8,14 L12,12 L18,10 L58,10 L86,12 L94,14 L86,16 L58,18 L18,18 L12,16 Z M22,10 L25,7 L28,10 M66,10 L69,7 L72,10',
        medium:   'M4,14 L8,13 L12,10 L52,10 L88,12 L96,14 L88,16 L52,18 L12,18 L8,15 Z M20,10 L24,6 L28,10 M68,10 L72,6 L76,10',
        large:    'M2,14 L6,12 L10,9 L38,9 L48,9 L52,9 L88,11 L98,13 L98,15 L88,17 L52,17 L48,17 L38,17 L10,17 L6,15 Z M14,9 L18,5 L22,9 M30,9 L34,6 L38,9 M72,9 L76,5 L80,9',
        classic:  'M3,14 L7,12 L11,9 L40,9 L50,9 L86,11 L96,13 L96,15 L86,17 L50,17 L40,17 L11,17 L7,15 Z M15,9 L18,5 L21,9 M70,9 L74,5 L78,9 M92,8 L96,4 L96,12 L92,14 Z',
        cargo:    'M4,15 L10,13 L14,11 L50,11 L86,13 L96,15 L86,17 L50,19 L14,19 L10,17 Z M18,11 L22,8 L26,11 M70,11 L74,8 L78,11 M30,11 L66,11 L66,19 L30,19 Z',
        passenger:'M4,14 L8,13 L12,10 L52,10 L88,12 L96,14 L88,16 L52,18 L12,18 L8,15 Z M20,10 L24,6 L28,10 M68,10 L72,6 L76,10',
    };

    function hashId(id) {
        let h = 0;
        const s = String(id || 'ac');
        for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0;
        return Math.abs(h);
    }

    function colorForAircraft(id, category) {
        const h = hashId(id);
        const base = LIVERY_PALETTE[h % LIVERY_PALETTE.length];
        const alt = LIVERY_PALETTE[(h + (category || '').length * 7) % LIVERY_PALETTE.length];
        return { body: base, accent: alt };
    }

    function categoryMeta(category) {
        return CATEGORY_META[category] || CATEGORY_META['소형'];
    }

    function resolveVisual(ac, loadout, opts) {
        const meta = categoryMeta(ac?.category || ac?.type);
        const ld = loadout || ac?.loadout_details || ac?.loadout || {};
        const livery = ld.livery || {};
        const trail = ld.trail || {};
        const sticker = ld.sticker || {};
        const hangarBg = ld.hangar_bg || {};
        const radarSkin = ld.radar_skin || {};
        const randomColors = colorForAircraft(ac?.id || ac?.name, ac?.category);
        const useRandom = opts?.codex || opts?.forceRandomColor;
        const displayColor = ac?.display_color;
        let bodyColor = livery.color || displayColor || (useRandom ? randomColors.body : meta.body);
        if (useRandom && !livery.color && displayColor) bodyColor = displayColor;
        if (useRandom && !livery.color && !displayColor) bodyColor = randomColors.body;
        const accentColor = ac?.accent_color || randomColors.accent || meta.accent;
        const trailColor = trail.color || '#a855f7';
        const bgColor = hangarBg.color || accentColor;
        return {
            meta,
            bodyColor,
            accentColor,
            trailColor,
            stickerEmoji: sticker.emoji || ac?.sticker_emoji || '',
            liveryName: livery.name || '',
            radarColor: radarSkin.color || trailColor,
            hangarBgColor: bgColor,
            hangarBgEmoji: hangarBg.emoji || '',
        };
    }

    function shapePath(meta) {
        return SHAPES[meta.shape] || SHAPES.medium;
    }

    function buildPlaneSvg(visual, opts) {
        const size = opts?.size || 120;
        const meta = visual.meta;
        const scale = meta.scale * (opts?.scaleMul || 1);
        const w = size;
        const h = Math.round(size * 0.45);
        const path = shapePath(meta);
        const isCargo = meta.shape === 'cargo';
        const isLarge = meta.shape === 'large' || meta.shape === 'classic';
        const sticker = visual.stickerEmoji
            ? `<text x="${w * 0.72}" y="${h * 0.35}" font-size="${Math.round(size * 0.2)}" text-anchor="middle">${visual.stickerEmoji}</text>`
            : '';
        const cargoMark = isCargo
            ? `<rect x="${w*0.38}" y="${h*0.38}" width="${w*0.24}" height="${h*0.28}" rx="2" fill="rgba(255,255,255,0.15)" stroke="rgba(255,255,255,0.35)" stroke-width="0.8"/>`
            : '';
        const wingStripe = `<path d="M12,14 L88,14" stroke="rgba(255,255,255,0.3)" stroke-width="${isLarge ? 1.2 : 0.8}"/>`;
        const tailFin = meta.shape === 'classic'
            ? `<path d="M${w*0.88},${h*0.25} L${w*0.96},${h*0.08} L${w*0.92},${h*0.32} Z" fill="${visual.accentColor}" opacity="0.9"/>`
            : '';
        return `<svg viewBox="0 0 100 22" width="${w}" height="${h}" style="transform:scale(${scale});transform-origin:center" aria-hidden="true" class="ac-plane-svg ac-plane-${meta.shape}">
            <path d="${path}" fill="${visual.bodyColor}" stroke="#0a0a0a" stroke-width="1.1" opacity="0.96"/>
            ${wingStripe}${cargoMark}${tailFin}${sticker}
        </svg>`;
    }

    function buildPreviewHtml(ac, loadout, opts) {
        if (!ac) return '';
        const codex = opts?.codex;
        const visual = resolveVisual(ac, loadout, opts);
        const meta = visual.meta;
        const large = opts?.large !== false;
        const illustration = ac.illustration;
        const useImage = !codex && opts?.preferImage !== false && illustration && ac.owned;
        const inner = useImage
            ? `<img src="${illustration}" alt="${ac.name || ''}" class="ac-preview-img" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"/>
               <div class="ac-preview-svg-wrap" style="display:none">${buildPlaneSvg(visual, { size: large ? 140 : 90 })}</div>`
            : `<div class="ac-preview-svg-wrap">${buildPlaneSvg(visual, { size: large ? 140 : 90 })}</div>`;
        const stickerBadge = visual.stickerEmoji
            ? `<span class="ac-preview-sticker">${visual.stickerEmoji}</span>` : '';
        const liveryBadge = visual.liveryName
            ? `<span class="ac-preview-livery">${visual.liveryName}</span>`
            : (codex ? `<span class="ac-preview-livery ac-codex-color-dot" style="background:${visual.bodyColor}"></span>` : '');
        return `<div class="ac-preview ${meta.cls} ${large ? 'ac-preview-lg' : 'ac-preview-sm'} ${codex ? 'ac-codex-card' : ''}" style="--ac-body:${visual.bodyColor};--ac-bg:${visual.hangarBgColor}">
            <div class="ac-preview-bg"></div>
            <div class="ac-preview-body">${inner}${stickerBadge}</div>
            <div class="ac-preview-label">${meta.label}${liveryBadge}</div>
        </div>`;
    }

    function buildCodexHtml(ac, loadout, opts) {
        return buildPreviewHtml(ac, loadout, { ...opts, codex: true, preferImage: false, large: false, forceRandomColor: true });
    }

    function buildLockedCodexHtml(category) {
        const meta = categoryMeta(category || '소형');
        const colors = colorForAircraft('locked-' + category, category);
        const visual = {
            meta,
            bodyColor: '#3a3a3c',
            accentColor: '#2c2c2e',
            stickerEmoji: '',
            hangarBgColor: '#111',
        };
        return `<div class="ac-preview ${meta.cls} ac-preview-sm ac-codex-card ac-codex-locked" style="--ac-body:#555;--ac-bg:#111">
            <div class="ac-preview-bg"></div>
            <div class="ac-preview-body ac-preview-svg-wrap" style="opacity:0.35">${buildPlaneSvg(visual, { size: 80 })}</div>
            <div class="ac-preview-label" style="color:#666">${meta.label}</div>
            <div class="ac-codex-lock">❓</div>
        </div>`;
    }

    function previewCss() {
        return `.ac-preview{position:relative;border-radius:16px;overflow:hidden;border:2px solid var(--ac-body,#33ff33);min-height:100px;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:12px 8px}
.ac-preview-bg{position:absolute;inset:0;background:linear-gradient(160deg,var(--ac-bg,#111) 0%,#0a0a0a 70%);opacity:.85}
.ac-preview-body{position:relative;z-index:1;display:flex;align-items:center;justify-content:center;min-height:70px}
.ac-preview-svg-wrap{display:flex;align-items:center;justify-content:center}
.ac-preview-img{max-height:72px;max-width:100%;object-fit:contain;filter:drop-shadow(0 4px 8px rgba(0,0,0,.5))}
.ac-preview-lg{min-height:160px}.ac-preview-lg .ac-preview-img{max-height:100px}
.ac-preview-sm{min-height:88px;padding:8px 6px}.ac-preview-sm .ac-preview-body{min-height:52px}
.ac-preview-label{position:relative;z-index:1;font-size:10px;font-weight:700;margin-top:6px;color:var(--ac-body,#33ff33);display:flex;align-items:center;gap:4px}
.ac-preview-livery{font-size:9px;opacity:.85;font-weight:500}
.ac-preview-sticker{position:absolute;top:4px;right:8px;font-size:20px;z-index:2;filter:drop-shadow(0 0 4px rgba(0,0,0,.8))}
.ac-preview.cat-small{border-color:#33ff33}.ac-preview.cat-medium{border-color:#0A84FF}
.ac-preview.cat-large{border-color:#ffaa00}.ac-preview.cat-cargo{border-color:#a78bfa}
.ac-preview.cat-regional{border-color:#4da8da}
.ac-codex-card{width:100%;min-height:96px;border-width:2px;box-shadow:0 4px 12px rgba(0,0,0,.35)}
.ac-codex-color-dot{width:10px;height:10px;border-radius:50%;display:inline-block;border:1px solid rgba(255,255,255,.4);flex-shrink:0}
.ac-codex-locked{border-color:#444!important;opacity:.7}
.ac-codex-lock{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:28px;z-index:3;pointer-events:none;text-shadow:0 2px 8px #000}
.ac-plane-svg{filter:drop-shadow(0 3px 6px rgba(0,0,0,.45))}`;
    }

    global.AircraftVisual = {
        categoryMeta,
        resolveVisual,
        buildPlaneSvg,
        buildPreviewHtml,
        buildCodexHtml,
        buildLockedCodexHtml,
        colorForAircraft,
        previewCss,
        CATEGORY_META,
        LIVERY_PALETTE,
    };
})(typeof window !== 'undefined' ? window : globalThis);