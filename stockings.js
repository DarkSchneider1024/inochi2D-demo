// Sock choices belong to the web player, so older INP files can use them too.
export const STOCKINGS_PARAM = 'Outfit:: Stockings';

export function installStockings(puppet) {
  const id = puppet.json.meta?.name;
  if (!['new_carol', 'new_carol_side', 'new_carol_sit', 'carol_v3'].includes(id)) return;
  const parts = puppet.parts.filter((part) => /^(?:學院_)?(?:大腿|小腿|腿)_[RL近遠]$/.test(part.name));
  if (!parts.length) return;
  puppet.stockingParts = parts;
  for (const part of parts) {
    // The front-view texture includes the boot. Split walking legs have separate boot parts.
    part.stockingCut = id.startsWith('new_carol') && /^腿_/.test(part.name) ? 0.68 : 1;
    // The older academy leg already has black tights and its own brown boot in one texture.
    if (id === 'carol_v3' && part.name.startsWith('學院_')) part.stockingCut = 0;
  }
  if (puppet.byName[STOCKINGS_PARAM]) return;
  const parameter = {
    uuid: -20261120, name: STOCKINGS_PARAM, is_vec2: false,
    min: [-1, 0], max: [1, 0], defaults: [-1, 0], value: [-1, 0],
    axis_points: [[0, 0.5, 1], [0]], bindings: [],
  };
  puppet.params.push(parameter);
  puppet.byName[STOCKINGS_PARAM] = parameter;
}

export function updateStockings(puppet) {
  if (!puppet.stockingParts) return;
  const choice = puppet.byName[STOCKINGS_PARAM].value[0];
  const academy = puppet.byName['Mix:: Legs:: Academy'] ?? puppet.byName['Outfit:: Academy'];
  const strength = choice < 0 ? (academy?.value[0] ?? 0) : choice;
  for (const part of puppet.stockingParts) part.stocking = Math.max(0, Math.min(1, strength));
}

export const STOCKINGS_GLSL = `
  uniform float uStocking, uStockingCut;
  vec4 dressStocking(vec4 texel, vec2 uv) {
    if (uStocking <= 0. || texel.a <= 0. || uv.y >= uStockingCut) return texel;
    vec3 color = texel.rgb / texel.a;
    float light = dot(color, vec3(.299, .587, .114));
    // At the curved boot opening, retain the brown leather and orange laces.
    float boot = uStockingCut < .99 && uv.y > .60
      ? smoothstep(.13, .25, color.r - color.b) * (1. - smoothstep(.55, .72, light)) : 0.;
    float shade = .045 + .145 * light;
    vec3 charcoal = vec3(shade * .94, shade * .95, shade);
    texel.rgb = mix(texel.rgb, charcoal * texel.a, uStocking * (1. - boot));
    return texel;
  }
`;
