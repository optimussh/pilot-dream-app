/** 기종 카테고리별 실루엣·색상 미리보기 (창고·도감·로그북 공용) */
(function (global) {
    const CATEGORY_META = {
        '소형':      { cls: 'cat-small',    label: '소형',   body: '#33ff33', accent: '#1a5c2e', scale: 0.82, shape: 'passenger' },
        '리저널':    { cls: 'cat-regional', label: '리저널', body: '#4da8da', accent: '#1a4a6e', scale: 0.78, shape: 'passenger' },
        '중형':      { cls: 'cat-medium',   label: '중형',   body: '#0A84FF', accent: '#003d80', scale: 1.0,  shape: 'passenger' },
        '대형':      { cls: 'cat-large',    label: '대형',   body: '#ffaa00', accent: '#8a5a00', scale: 1.18, shape: 'passenger' },
        '클래식':    { cls: 'cat-large',    label: '클래식', body: '#ffaa00', accent: '#8a5a00', scale: 1.12, shape: 'passenger' },
        '화물기':    { cls: 'cat-cargo',    label: '화물기', body: '#a78bfa', accent: '#4c1d95', scale: 1.05, shape: 'cargo' },
    };

    const SHAPES = {
        passenger: 'M4,14 L8,13 L12,10 L52,10 L88,12 L96,14 L88,16 L52,18 L12,18 L8,15 Z M20,10 L24,6 L28,10 M68,10 L72,6 L76,10',
        cargo:     'M4,15 L10,13 L14,11 L50,11 L86,13 L96,15 L86,17 L50,19 L14,19 L10,17 Z M18,11 L22,8 L26,11 M70,11 L74,8 L78,11 M30,11 L66,11 L66,19 L30,19 Z',
    };

    function categoryMeta(category) {
        return CATEGORY_META[category] || CATEGORY_META['소형'];
    }

    function resolveVisual(ac, loadout) {
        const meta = categoryMeta(ac?.category || ac?.type);
        const ld = loadout || ac?.loadout_details || ac?.loadout || {};
        const livery = ld.livery || {};
        const trail = ld.trail || {};
        const sticker = ld.sticker || {};
        const hangarBg = ld.hangar_bg || {};
        const radarSkin = ld.radar_skin || {};
        const bodyColor = livery.color || meta.body;
        const trailColor = trail.color || '#a855f7';
        const bgColor = hangarBg.color || meta.accent;
        return {
            meta,
            bodyColor,
            trailColor,
            stickerEmoji: sticker.emoji || '',
            liveryName: livery.name || '',
            radarColor: radarSkin.color || trailColor,
            hangarBgColor: bgColor,
            hangarBgEmoji: hangarBg.emoji || '',
        };
    }

    function buildPlaneSvg(visual, opts) {
        const size = opts?.size || 120;
        const meta = visual.meta;
        const scale = meta.scale * (opts?.scaleMul || 1);
        const w = size;
        const h = Math.round(size * 0.45);
        const path = SHAPES[meta.shape] || SHAPES.passenger;
        const sticker = visual.stickerEmoji
            ? `<text x="${w * 0.72}" y="${h * 0.35}" font-size="${Math.round(size * 0.22)}" text-anchor="middle">${visual.stickerEmoji}</text>`
            : '';
        const cargoMark = meta.shape === 'cargo'
            ? `<text x="${w * 0.5}" y="${h * 0.62}" font-size="${Math.round(size * 0.16)}" fill="#fff" text-anchor="middle" opacity="0.9">📦</text>`
            : '';
        return `<svg viewBox="0 0 100 22" width="${w}" height="${h}" style="transform:scale(${scale}); transform-origin:center" aria-hidden="true">
            <path d="${path}" fill="${visual.bodyColor}" stroke="#111" stroke-width="1.2" opacity="0.95"/>
            <path d="M12,14 L88,14" stroke="rgba(255,255,255,0.25)" stroke-width="0.8"/>
            ${cargoMark}${sticker}
        </svg>`;
    }

    function buildPreviewHtml(ac, loadout, opts) {
        if (!ac) return '';
        const visual = resolveVisual(ac, loadout);
        const meta = visual.meta;
        const large = opts?.large !== false;
        const illustration = ac.illustration;
        const useImage = opts?.preferImage !== false && illustration && ac.owned;
        const inner = useImage
            ? `<img src="${illustration}" alt="${ac.name || ''}" class="ac-preview-img" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"/>
               <div class="ac-preview-svg-wrap" style="display:none">${buildPlaneSvg(visual, { size: large ? 140 : 90 })}</div>`
            : `<div class="ac-preview-svg-wrap">${buildPlaneSvg(visual, { size: large ? 140 : 90 })}</div>`;
        const stickerBadge = visual.stickerEmoji
            ? `<span class="ac-preview-sticker">${visual.stickerEmoji}</span>` : '';
        const liveryBadge = visual.liveryName
            ? `<span class="ac-preview-livery">${visual.liveryName}</span>` : '';
        return `<div class="ac-preview ${meta.cls} ${large ? 'ac-preview-lg' : 'ac-preview-sm'}" style="--ac-body:${visual.bodyColor};--ac-bg:${visual.hangarBgColor}">
            <div class="ac-preview-bg"></div>
            <div class="ac-preview-body">${inner}${stickerBadge}</div>
            <div class="ac-preview-label">${meta.label}${liveryBadge}</div>
        </div>`;
    }

    function previewCss() {
        return `.ac-preview{position:relative;border-radius:16px;overflow:hidden;border:2px solid var(--ac-body,#33ff33);min-height:100px;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:12px 8px}
.ac-preview-bg{position:absolute;inset:0;background:linear-gradient(160deg,var(--ac-bg,#111) 0%,#0a0a0a 70%);opacity:.85}
.ac-preview-body{position:relative;z-index:1;display:flex;align-items:center;justify-content:center;min-height:70px}
.ac-preview-svg-wrap{display:flex;align-items:center;justify-content:center}
.ac-preview-img{max-height:72px;max-width:100%;object-fit:contain;filter:drop-shadow(0 4px 8px rgba(0,0,0,.5))}
.ac-preview-lg{min-height:160px}.ac-preview-lg .ac-preview-img{max-height:100px}
.ac-preview-label{position:relative;z-index:1;font-size:10px;font-weight:700;margin-top:6px;color:var(--ac-body,#33ff33)}
.ac-preview-livery{display:block;font-size:9px;opacity:.85;font-weight:500;margin-top:2px}
.ac-preview-sticker{position:absolute;top:4px;right:8px;font-size:20px;z-index:2;filter:drop-shadow(0 0 4px rgba(0,0,0,.8))}
.ac-preview.cat-small{border-color:#33ff33}.ac-preview.cat-medium{border-color:#0A84FF}
.ac-preview.cat-large{border-color:#ffaa00}.ac-preview.cat-cargo{border-color:#a78bfa}
.ac-preview.cat-regional{border-color:#4da8da}`;
    }

    global.AircraftVisual = {
        categoryMeta,
        resolveVisual,
        buildPlaneSvg,
        buildPreviewHtml,
        previewCss,
        CATEGORY_META,
    };
})(typeof window !== 'undefined' ? window : globalThis);