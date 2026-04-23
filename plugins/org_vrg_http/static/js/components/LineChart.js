// Компонент линейного графика на SVG (без внешних зависимостей)
const LineChart = {
  props: {
    data: { type: Array, required: true }, // [{ts, dt, value}]
    unit: { type: String, default: '' }
  },

  computed: {
    sorted() {
      return [...this.data].sort((a, b) => a.ts - b.ts);
    },

    chart() {
      const d = this.sorted;
      if (d.length === 0) return null;

      const W = 800, H = 300;
      const padL = 55, padR = 20, padT = 20, padB = 50;
      const w = W - padL - padR;
      const h = H - padT - padB;

      const minTs = d[0].ts;
      const maxTs = d[d.length - 1].ts;
      const tsRange = maxTs - minTs || 1;

      const values = d.map(p => p.value);
      const minVal = Math.min(...values);
      const maxVal = Math.max(...values);
      const valPad = (maxVal - minVal) * 0.1 || 1;
      const yMin = minVal - valPad;
      const yMax = maxVal + valPad;
      const valRange = yMax - yMin;

      const toX = ts => padL + ((ts - minTs) / tsRange) * w;
      const toY = val => padT + h - ((val - yMin) / valRange) * h;

      // Линия данных
      const path = d.map((p, i) =>
        `${i === 0 ? 'M' : 'L'}${toX(p.ts).toFixed(1)},${toY(p.value).toFixed(1)}`
      ).join('');

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

      // Метки Y — 5 равномерно распределённых значений
      const yTicks = Array.from({ length: 5 }, (_, i) => {
        const val = yMin + (valRange / 4) * i;
        return { y: toY(val), label: val.toFixed(1) };
      });

      return { W, H, padL, padR, padT, padB, w, h, path, xTicks, yTicks };
    }
  },

  template: `
    <div style="width: 100%; overflow-x: auto;">
      <div v-if="sorted.length === 0" style="text-align: center; padding: 40px; color: var(--color-text-secondary);">
        {{ $t('http.common.no_data') }}
      </div>
      <svg
        v-else
        :viewBox="'0 0 ' + chart.W + ' ' + chart.H"
        style="width: 100%; min-width: 320px; display: block;"
        xmlns="http://www.w3.org/2000/svg"
      >
        <!-- Фон -->
        <rect x="0" y="0" :width="chart.W" :height="chart.H" fill="var(--color-bg-secondary, #1a1a2e)" rx="8"/>

        <!-- Горизонтальные линии сетки -->
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

        <!-- Метки единицы измерения на Y -->
        <text
          v-if="unit"
          :x="chart.padL - 6" :y="chart.padT - 6"
          text-anchor="end" font-size="11"
          fill="var(--color-text-secondary, #888)"
        >{{ unit }}</text>

        <!-- Метки X -->
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

        <!-- Линия данных (заливка под линией) -->
        <path
          :d="chart.path + 'L' + (chart.W - chart.padR) + ',' + (chart.padT + chart.h) + 'L' + chart.padL + ',' + (chart.padT + chart.h) + 'Z'"
          fill="var(--color-accent, #5b7fc4)" opacity="0.1"
        />

        <!-- Линия данных -->
        <path
          :d="chart.path"
          fill="none"
          stroke="var(--color-accent, #5b7fc4)"
          stroke-width="2"
          stroke-linejoin="round"
          stroke-linecap="round"
        />
      </svg>
    </div>
  `
};
