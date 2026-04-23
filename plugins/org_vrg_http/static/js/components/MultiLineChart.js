// Компонент линейного графика с поддержкой нескольких линий (SVG, без внешних зависимостей)
const MULTI_LINE_COLORS = [
  'var(--color-accent, #5b7fc4)',
  '#e05555',
  '#55a855',
  '#e09055'
];

const MultiLineChart = {
  props: {
    series: { type: Array, required: true }, // [{name: str, data: [{ts, dt, value}]}]
    unit: { type: String, default: '' }
  },

  computed: {
    hasData() {
      return this.series.some(s => s.data && s.data.length > 0);
    },

    colors() {
      return this.series.map((_, i) => MULTI_LINE_COLORS[i] || MULTI_LINE_COLORS[MULTI_LINE_COLORS.length - 1]);
    },

    chart() {
      if (!this.hasData) return null;

      const W = 800, H = 300;
      const padL = 55, padR = 20, padT = 20, padB = 50;
      const w = W - padL - padR;
      const h = H - padT - padB;

      const sorted = this.series.map((s, i) => ({
        name: s.name,
        color: MULTI_LINE_COLORS[i] || MULTI_LINE_COLORS[MULTI_LINE_COLORS.length - 1],
        data: [...s.data].sort((a, b) => a.ts - b.ts)
      }));

      let minTs = Infinity, maxTs = -Infinity;
      const allValues = [];
      for (const s of sorted) {
        for (const p of s.data) {
          if (p.ts < minTs) minTs = p.ts;
          if (p.ts > maxTs) maxTs = p.ts;
          allValues.push(p.value);
        }
      }
      const tsRange = maxTs - minTs || 1;
      const minVal = Math.min(...allValues);
      const maxVal = Math.max(...allValues);
      const valPad = (maxVal - minVal) * 0.1 || 1;
      const yMin = minVal - valPad;
      const yMax = maxVal + valPad;
      const valRange = yMax - yMin;

      const toX = ts => padL + ((ts - minTs) / tsRange) * w;
      const toY = val => padT + h - ((val - yMin) / valRange) * h;

      const paths = sorted.map(s => ({
        name: s.name,
        color: s.color,
        d: s.data.map((p, j) =>
          `${j === 0 ? 'M' : 'L'}${toX(p.ts).toFixed(1)},${toY(p.value).toFixed(1)}`
        ).join('')
      }));

      // Метки X: метка на каждый ровный час + последний timestamp
      const fmtTs = ts => {
        const d = new Date(ts * 1000);
        return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
      };
      const oneHour = 3600;
      const xTicks = [];
      for (let h = Math.ceil(minTs / oneHour) * oneHour; h < maxTs; h += oneHour) {
        xTicks.push({ x: toX(h), label: fmtTs(h) });
      }
      xTicks.push({ x: toX(maxTs), label: fmtTs(maxTs) });

      const yTicks = Array.from({ length: 5 }, (_, i) => {
        const val = yMin + (valRange / 4) * i;
        return { y: toY(val), label: val.toFixed(1) };
      });

      return { W, H, padL, padR, padT, padB, w, h, paths, xTicks, yTicks };
    }
  },

  template: `
    <div style="width: 100%; overflow-x: auto;">
      <div v-if="!hasData" style="text-align: center; padding: 40px; color: var(--color-text-secondary);">
        {{ $t('http.common.no_data') }}
      </div>
      <div v-else>
        <!-- Легенда (только при нескольких сериях) -->
        <div v-if="series.length > 1" style="display: flex; gap: var(--spacing-md); margin-bottom: var(--spacing-sm); flex-wrap: wrap;">
          <div
            v-for="(s, i) in series"
            :key="s.name"
            style="display: flex; align-items: center; gap: 4px; font-size: 0.8rem; color: var(--color-text-secondary);"
          >
            <span :style="{ display: 'inline-block', width: '20px', height: '3px', background: colors[i], borderRadius: '2px' }"></span>
            {{ s.name }}
          </div>
        </div>

        <svg
          :viewBox="'0 0 ' + chart.W + ' ' + chart.H"
          style="width: 100%; min-width: 320px; display: block;"
          xmlns="http://www.w3.org/2000/svg"
        >
          <!-- Фон -->
          <rect x="0" y="0" :width="chart.W" :height="chart.H" fill="var(--color-bg-secondary, #1a1a2e)" rx="8"/>

          <!-- Горизонтальные линии сетки и метки Y -->
          <g v-for="tick in chart.yTicks" :key="tick.y">
            <line
              :x1="chart.padL" :y1="tick.y"
              :x2="chart.W - chart.padR" :y2="tick.y"
              stroke="var(--color-border, #333)" stroke-width="1" stroke-dasharray="4,4"
            />
            <text
              :x="chart.padL - 6" :y="tick.y + 4"
              text-anchor="end" font-size="11"
              fill="var(--color-text-secondary, #888)"
            >{{ tick.label }}</text>
          </g>

          <!-- Единица измерения оси Y -->
          <text
            v-if="unit"
            :x="chart.padL - 6" :y="chart.padT - 6"
            text-anchor="end" font-size="11"
            fill="var(--color-text-secondary, #888)"
          >{{ unit }}</text>

          <!-- Вертикальные линии сетки и метки X -->
          <g v-for="(tick, i) in chart.xTicks" :key="i">
            <line
              :x1="tick.x" :y1="chart.padT"
              :x2="tick.x" :y2="chart.padT + chart.h"
              stroke="var(--color-border, #333)" stroke-width="1" stroke-dasharray="4,4" opacity="0.5"
            />
            <text
              :x="tick.x" :y="chart.padT + chart.h + 18"
              text-anchor="middle" font-size="10"
              fill="var(--color-text-secondary, #888)"
            >{{ tick.label }}</text>
          </g>

          <!-- Рамка графика -->
          <rect
            :x="chart.padL" :y="chart.padT"
            :width="chart.w" :height="chart.h"
            fill="none" stroke="var(--color-border, #444)" stroke-width="1"
          />

          <!-- Линии данных -->
          <path
            v-for="p in chart.paths"
            :key="p.name"
            :d="p.d"
            fill="none"
            :stroke="p.color"
            stroke-width="2"
            stroke-linejoin="round"
            stroke-linecap="round"
          />
        </svg>
      </div>
    </div>
  `
};
