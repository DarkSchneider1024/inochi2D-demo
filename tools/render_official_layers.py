"""Rasterize official meshes with the site's renderer before running layer QA.
Requires playwright and Microsoft Edge. Preserves UVs, transforms and masks.
"""
import base64
import functools
import http.server
import io
import threading
from playwright.sync_api import sync_playwright
from PIL import Image


def render_official(root, mid):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=root)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, channel="msedge")
            page = browser.new_page()
            page.route('**/__layer_export__', lambda route: route.fulfill(body='<html></html>', content_type='text/html'))
            page.goto(f'http://127.0.0.1:{server.server_port}/__layer_export__')
            result = page.evaluate('''async (mid) => {
              const {loadINP, Puppet, Renderer} = await import('./inochi-full.js');
              const data = await loadINP(`models/official/${mid}.inp`);
              const p = new Puppet(data), cv = document.createElement('canvas'), r = new Renderer(cv);
              const all = p.parts.flatMap(n => Array.from(n.pos));
              const xs = all.filter((_,i) => i%2 === 0), ys = all.filter((_,i) => i%2);
              const x0 = Math.floor(Math.min(...xs))-4, y0 = Math.floor(Math.min(...ys))-4;
              const width = Math.ceil(Math.max(...xs))-x0+4, height = Math.ceil(Math.max(...ys))-y0+4;
              const scale = Math.min(1, 1600/Math.max(width,height));
              cv.width = Math.ceil(width*scale); cv.height = Math.ceil(height*scale);
              r.attach(p);
              const view = {cx:x0+width/2,cy:y0+height/2,scale};
              const parts = [];
              const ordered = [...p.drawList].sort((a,b)=>b.z-a.z).flatMap(n => n.type === 'Composite' ? [...n.sub].sort((a,b)=>b.z-a.z) : [n]);
              for(const [order,n] of ordered.entries()) {
                const hidden = !n.on || n.alpha < .05, alpha=n.alpha, on=n.on, blend=n.blend_mode;
                p.drawList = [n]; n.on=true; n.alpha=1; n.blend_mode='Normal';
                r.draw(view);
                parts.push({name:n.name,uuid:n.uuid,z:ordered.length-order,hidden,group:n.parent?.name || '',png:cv.toDataURL('image/png')});
                n.alpha=alpha; n.on=on; n.blend_mode=blend;
              }
              return {json:data.json,parts};
            }''', mid)
            browser.close()
        textures, parts = [], []
        for n in result['parts']:
            im = Image.open(io.BytesIO(base64.b64decode(n.pop('png').split(',')[1]))).convert('RGBA')
            box = im.getbbox() or (0, 0, 1, 1)
            buf = io.BytesIO(); im.crop(box).save(buf, format='PNG')
            n.update(tex=len(textures), x0=box[0], y0=box[1], x1=box[2], y1=box[3])
            textures.append(buf.getvalue()); parts.append(n)
        return result['json'], textures, parts
    finally:
        server.shutdown(); server.server_close()
