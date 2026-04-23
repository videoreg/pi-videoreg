// Компонент страницы статистики (CPU температура, PiSugar заряд, трафик)
const StatComponent = {
  components: { TabSwitch, LineChart, MultiLineChart },
  emits: ['navigate'],

  template: `
    <div>
      <div class="page-header">
        <h1 class="page-title">{{ $t('http.stat.title') }}</h1>
        <div style="display: flex; gap: var(--spacing-sm);">
          <div v-if="loading" class="spinner spinner-sm"></div>
          <button v-else class="btn btn-icon" @click="loadData" :title="$t('http.common.refresh')">↻</button>
        </div>
      </div>

      <tab-switch
        v-if="everLoaded"
        v-model="activeTab"
        :tabs="tabList"
        style="margin-bottom: var(--spacing-lg); margin-right: var(--spacing-md);"
      ></tab-switch>

      <div v-if="currentAvailableDates.length > 1" class="tab-switch" style="margin-bottom: var(--spacing-lg); flex-wrap: wrap;">
        <button
          v-for="date in currentAvailableDates"
          :key="date"
          class="tab-button"
          :class="{ active: date === currentSelectedDate }"
          @click="selectDate(date)"
        >{{ formatDate(date) }}</button>
      </div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <div v-if="everLoaded">
        <!-- CPU температура -->
        <div v-if="activeTab === 'cpu'" class="info-block">
          <div style="margin-bottom: var(--spacing-md);">
            <span style="font-weight: 600;">{{ $t('http.stat.cpu_temp_title') }}</span>
            <span v-if="tempData.length > 0" style="margin-left: var(--spacing-md); color: var(--color-text-secondary); font-size: 0.875rem;">
              {{ tempDate }} &middot; {{ tempData.length }} {{ $t('http.stat.points') }}
            </span>
          </div>
          <line-chart :data="tempData" unit="°C"></line-chart>
        </div>

        <!-- PiSugar заряд -->
        <div v-if="activeTab === 'pisugar'" class="info-block">
          <div style="margin-bottom: var(--spacing-md);">
            <span style="font-weight: 600;">{{ $t('http.stat.pisugar_title') }}</span>
            <span v-if="pisugarData.length > 0" style="margin-left: var(--spacing-md); color: var(--color-text-secondary); font-size: 0.875rem;">
              {{ pisugarDate }} &middot; {{ pisugarData.length }} {{ $t('http.stat.points') }}
            </span>
          </div>
          <line-chart :data="pisugarData" unit="%"></line-chart>
        </div>

        <!-- Трафик -->
        <div v-if="activeTab === 'traffic'">
          <div class="info-block" style="margin-bottom: var(--spacing-lg);">
            <div style="margin-bottom: var(--spacing-md);">
              <span style="font-weight: 600;">Download</span>
              <span v-if="trafficDate" style="margin-left: var(--spacing-md); color: var(--color-text-secondary); font-size: 0.875rem;">
                {{ trafficDate }}
              </span>
            </div>
            <multi-line-chart :series="downloadSeries" :unit="$t('http.stat.traffic_unit')"></multi-line-chart>
          </div>
          <div class="info-block">
            <div style="margin-bottom: var(--spacing-md);">
              <span style="font-weight: 600;">Upload</span>
            </div>
            <multi-line-chart :series="uploadSeries" :unit="$t('http.stat.traffic_unit')"></multi-line-chart>
          </div>
        </div>

      </div>
    </div>
  `,

  data() {
    return {
      activeTab: 'cpu',
      tabs: [],
      // CPU / PiSugar
      selectedDate: null,
      availableDates: [],
      tempData: [],
      tempDate: null,
      pisugarData: [],
      pisugarDate: null,
      // Трафик
      trafficSelectedDate: null,
      trafficAvailableDates: [],
      trafficInterfaces: [],
      trafficSeries: {},
      trafficDate: null,
      //
      cpuPisugarLoaded: false,
      trafficLoaded: false,
      everLoaded: false,
      loading: false,
      error: ''
    };
  },

  computed: {
    tabList() {
      return [
        { value: 'cpu', label: this.$t('http.stat.tab_cpu') },
        { value: 'pisugar', label: 'PiSugar' },
        { value: 'traffic', label: this.$t('http.stat.tab_traffic') }
      ];
    },

    currentAvailableDates() {
      return this.activeTab === 'traffic' ? this.trafficAvailableDates : this.availableDates;
    },

    currentSelectedDate() {
      return this.activeTab === 'traffic' ? this.trafficSelectedDate : this.selectedDate;
    },

    downloadSeries() {
      return this.trafficInterfaces.map(iface => ({
        name: iface,
        data: (this.trafficSeries[iface] || []).map(p => ({ ts: p.ts, dt: p.dt, value: p.download }))
      }));
    },

    uploadSeries() {
      return this.trafficInterfaces.map(iface => ({
        name: iface,
        data: (this.trafficSeries[iface] || []).map(p => ({ ts: p.ts, dt: p.dt, value: p.upload }))
      }));
    }
  },

  methods: {
    formatDate(dateStr) {
      // dateStr формат YYYY-MM-DD → DD.MM
      const parts = dateStr.split('-');
      if (parts.length !== 3) return dateStr;
      return `${parts[2]}.${parts[1]}`;
    },

    selectDate(date) {
      if (this.activeTab === 'traffic') {
        this.trafficSelectedDate = date;
        this.loadTrafficData();
      } else {
        this.selectedDate = date;
        this.loadCpuPisugarData();
      }
    },

    async loadCpuPisugarData() {
      const dateParam = this.selectedDate ? `?date=${this.selectedDate}` : '';
      const [tempRes, pisugarRes] = await Promise.all([
        fetch(`/api/stat/temp${dateParam}`, { credentials: 'same-origin' }),
        fetch(`/api/stat/pisugar${dateParam}`, { credentials: 'same-origin' })
      ]);

      if (!tempRes.ok || !pisugarRes.ok) {
        this.error = this.$t('http.stat.error_load');
        return;
      }

      const tempJson = await tempRes.json();
      const pisugarJson = await pisugarRes.json();

      this.tempData = tempJson.data || [];
      this.tempDate = tempJson.date || null;
      this.pisugarData = pisugarJson.data || [];
      this.pisugarDate = pisugarJson.date || null;
      this.availableDates = tempJson.available_dates || [];
      this.cpuPisugarLoaded = true;

      if (this.availableDates.length > 0 && !this.selectedDate) {
        this.selectedDate = tempJson.date || this.availableDates[this.availableDates.length - 1];
      }
    },

    async loadTrafficData() {
      const dateParam = this.trafficSelectedDate ? `?date=${this.trafficSelectedDate}` : '';
      const res = await fetch(`/api/stat/traffic${dateParam}`, { credentials: 'same-origin' });

      if (!res.ok) {
        this.error = this.$t('http.stat.error_traffic');
        return;
      }

      const json = await res.json();
      this.trafficInterfaces = json.interfaces || [];
      this.trafficSeries = json.series || {};
      this.trafficDate = json.date || null;
      this.trafficAvailableDates = json.available_dates || [];
      this.trafficLoaded = true;

      if (this.trafficAvailableDates.length > 0 && !this.trafficSelectedDate) {
        this.trafficSelectedDate = json.date || this.trafficAvailableDates[this.trafficAvailableDates.length - 1];
      }
    },

    async loadActiveTab() {
      this.error = '';
      this.loading = true;
      try {
        if (this.activeTab === 'traffic') {
          await this.loadTrafficData();
        } else {
          await this.loadCpuPisugarData();
        }
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.loading = false;
        this.everLoaded = true;
      }
    },

    async loadData() {
      // Сброс всех данных
      this.selectedDate = null;
      this.availableDates = [];
      this.tempData = [];
      this.tempDate = null;
      this.pisugarData = [];
      this.pisugarDate = null;
      this.trafficSelectedDate = null;
      this.trafficAvailableDates = [];
      this.trafficInterfaces = [];
      this.trafficSeries = {};
      this.trafficDate = null;
      this.cpuPisugarLoaded = false;
      this.trafficLoaded = false;
      // Загружаем только активную вкладку
      await this.loadActiveTab();
    }
  },

  watch: {
    activeTab(newTab) {
      const loaded = newTab === 'traffic' ? this.trafficLoaded : this.cpuPisugarLoaded;
      if (!loaded) {
        this.loadActiveTab();
      }
    }
  },

  async mounted() {
    await this.loadActiveTab();
  }
};
