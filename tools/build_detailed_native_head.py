"""Build detailed native Inochi2D head parts with 9x9 ArtMeshes and XY keyforms."""
from __future__ import annotations
import io, json, random, struct
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'carrot_vtuber.inx'; OUT=ROOT/'carrot_vtuber_detailed_head.inx'
ASSETS=ROOT/'assets/generated_layers'; DEBUG=ROOT/'assets/native_head_layers'
MAGIC=b'TRNSRTS\0'; SIZE=512; GRID=9

def fit(path, width, y):
    im=Image.open(path).convert('RGBA'); ratio=width/im.width
    im=im.resize((width,round(im.height*ratio)),Image.Resampling.LANCZOS)
    c=Image.new('RGBA',(SIZE,SIZE)); c.alpha_composite(im,((SIZE-im.width)//2,y)); return c

def ellipse_patch(source, box, feather=5):
    mask=Image.new('L',source.size); d=ImageDraw.Draw(mask); d.ellipse(box,fill=255)
    mask=mask.filter(ImageFilter.GaussianBlur(feather)); out=source.copy(); out.putalpha(Image.composite(source.getchannel('A'),Image.new('L',source.size),mask)); return out,mask

def prepare_layers():
    DEBUG.mkdir(parents=True,exist_ok=True)
    face=fit(ASSETS/'face_base.png',300,135)
    layers={'hair_back':fit(ASSETS/'hair_back_full.png',430,25),'hair_front':fit(ASSETS/'hair_bangs.png',330,42)}
    boxes={'eye_l':(145,220,245,290),'eye_r':(267,220,367,290),'brow_l':(150,194,240,230),'brow_r':(272,194,362,230),'nose':(235,245,277,305),'mouth':(218,292,294,340)}
    base=face.copy()
    for name,box in boxes.items():
        patch,mask=ellipse_patch(face,box)
        layers[name]=patch
        a=base.getchannel('A'); erase=mask.point(lambda p:0 if p>24 else 255); base.putalpha(Image.composite(a,Image.new('L',a.size),erase))
    layers['face_base']=base
    for n,im in layers.items(): im.save(DEBUG/f'{n}.png')
    return layers

def mesh():
    verts=[]; uvs=[]; idx=[]
    for y in range(GRID):
        for x in range(GRID):
            u=x/(GRID-1); v=y/(GRID-1); verts += [(u-.5)*SIZE,(v-.5)*SIZE]; uvs += [u,v]
    for y in range(GRID-1):
        for x in range(GRID-1):
            a=y*GRID+x; b=a+1; c=a+GRID; d=c+1; idx += [a,c,b,b,c,d]
    return {'verts':verts,'uvs':uvs,'indices':idx,'origin':[0.0,0.0]}

def offsets(x,y,kind):
    out=[]; strength={'face_base':1,'hair_back':.65,'hair_front':.9,'eye_l':1.1,'eye_r':1.1,'brow_l':1,'brow_r':1,'nose':1.25,'mouth':1.15}[kind]
    for gy in range(GRID):
        v=gy/(GRID-1); cy=v-.5
        for gx in range(GRID):
            u=gx/(GRID-1); cx=u-.5
            # Ellipsoid projection: center travels most; far side compresses.
            dx=(x*30*(1-abs(cy)*.35)+x*cx*-18)*strength
            dy=(-y*22 + y*cy*20 + x*cx*cy*5)*strength
            out.append([round(dx,3),round(dy,3)])
    return out

def part(name,uuid,tex,z):
    return {'uuid':uuid,'name':name,'type':'Part','enabled':True,'zsort':z,'transform':{'trans':[0.,-420.,0.],'rot':[0.,0.,0.],'scale':[1.,1.]},'lockToRoot':False,'mesh':mesh(),'textures':[tex,4294967295,4294967295],'blend_mode':'Normal','tint':[1.,1.,1.],'screenTint':[0.,0.,0.],'emissionStrength':1.,'mask_threshold':.5,'opacity':1.}

def main():
    layers=prepare_layers(); raw=SRC.read_bytes(); n=struct.unpack('>I',raw[8:12])[0]; data=json.loads(raw[12:12+n]); tail=raw[12+n:]
    if not tail.startswith(b'TEX_SECT'): raise SystemExit('missing texture section')
    count=struct.unpack('>I',tail[8:12])[0]; pos=12; blobs=[]
    for _ in range(count):
        ln=struct.unpack('>I',tail[pos:pos+4])[0]; typ=tail[pos+4]; blobs.append((typ,tail[pos+5:pos+5+ln])); pos+=5+ln
    remainder=tail[pos:]
    old_head=next((n for n in data['nodes']['children'] if n.get('name')=='head'),None)
    if old_head: old_head['enabled']=False
    order=['hair_back','face_base','eye_l','eye_r','brow_l','brow_r','nose','mouth','hair_front']; uuids={}
    for i,name in enumerate(order):
        buf=io.BytesIO(); layers[name].save(buf,format='PNG'); blobs.append((0,buf.getvalue())); uuids[name]=random.randint(1,0xFFFFFFFE); data['nodes']['children'].append(part(name,uuids[name],count+i,-.20-i*.01))
    values_by_name={name:[[offsets(x,y,name) for y in (-1,0,1)] for x in (-1,0,1)] for name in order}
    bindings=[{'node':uuids[name],'param_name':'deform','values':values_by_name[name],'isSet':[[True]*3 for _ in range(3)],'interpolate_mode':'Linear'} for name in order]
    params=[p for p in (data.get('param') or []) if p.get('name')!='Angle X/Y']
    params.append({'uuid':random.randint(1,0xFFFFFFFE),'name':'Angle X/Y','is_vec2':True,'min':[-30.,-30.],'max':[30.,30.],'defaults':[0.,0.],'axis_points':[[0.,.5,1.],[0.,.5,1.]],'merge_mode':'Passthrough','bindings':bindings}); data['param']=params
    enc=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode(); out=bytearray(MAGIC+struct.pack('>I',len(enc))+enc+b'TEX_SECT'+struct.pack('>I',len(blobs)))
    for typ,blob in blobs: out+=struct.pack('>I',len(blob))+bytes([typ])+blob
    out+=remainder; OUT.write_bytes(out); print(f'Wrote {OUT.name}: {len(order)} parts, {GRID*GRID} vertices each, {len(bindings)} XY bindings, {len(blobs)} textures')

if __name__=='__main__': main()
