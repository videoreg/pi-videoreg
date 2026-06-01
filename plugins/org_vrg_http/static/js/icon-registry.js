// Global icon registry for VideoReg.
// Plugin icon modules (bundled in bundle.js) register their SVG paths here so the
// shared <icon> component can resolve them by name. Loaded before bundle.js.
const IconRegistry = (() => {
  const _paths = {};

  return {
    // register({ name: '<path .../>', ... })
    register(map) {
      Object.assign(_paths, map || {});
    },
    get(name) {
      return _paths[name] || null;
    },
  };
})();
