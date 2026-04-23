// Global i18n engine for VideoReg.
// Loaded before app.js; populated via VrgI18n.init() before Vue mounts.
const VrgI18n = (() => {
  let _locale = 'ru';
  let _data = {};

  function _pluralForm(n) {
    if (_locale === 'ru') {
      if (n % 10 === 1 && n % 100 !== 11) return 'one';
      if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100)) return 'few';
      return 'many';
    }
    return n === 1 ? 'one' : 'other';
  }

  function _interpolate(template, vars) {
    return template.replace(/\{\{(\w+)\}\}/g, (_, k) => (k in vars ? vars[k] : `{{${k}}}`));
  }

  return {
    async init() {
      try {
        const res = await fetch('/api/i18n', { credentials: 'same-origin' });
        if (res.ok) {
          const json = await res.json();
          _locale = json.locale || 'ru';
          _data = json.translations || {};
        }
      } catch (_) {}
    },

    t(key, vars = {}) {
      const val = _data[key];
      if (val == null) return key;
      const str = typeof val === 'object' ? (val.other ?? key) : val;
      return _interpolate(String(str), vars);
    },

    p(key, n, vars = {}) {
      const val = _data[key];
      if (val == null) return key;
      if (typeof val !== 'object') return _interpolate(String(val), { n, ...vars });
      const form = _pluralForm(n);
      const template = val[form] ?? val.other ?? key;
      return _interpolate(template, { n, ...vars });
    },

    get locale() { return _locale; },
  };
})();
