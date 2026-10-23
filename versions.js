// 版本號 (2026-10-23, user: 每個角色都給版號，版號就用日期)
// models/versions.json: { <model id = .inp file name>: { version: 'YYYY-MM-DD' (the build date), build: 'YYYYMMDD-HHMM',
// note, history: [...] } }, written by the builders (psd-create/src/inochi2d/demo_version.py); models nobody rebuilds
// carry their file's last build date. The build stamp goes into the model URL (?v=), so a rebuilt model is never
// served from the browser cache -- the old carol_v2 kept showing after a rebuild.
export const VERSIONS = await fetch('./models/versions.json', { cache: 'no-store' })
  .then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
export const idOf = (fileOrId) => fileOrId.split('/').pop().replace(/\.(inp|inx)$/, '');
export const verOf = (fileOrId) => VERSIONS[idOf(fileOrId)] || null;
// the model URL with its build stamp
export const vurl = (file) => { const v = verOf(file); return v ? `${file}?v=${v.build}` : file; };
// 'v2026-10-23' (empty when the model has no version)
export const vlabel = (fileOrId) => { const v = verOf(fileOrId); return v ? `v${v.version}` : ''; };
