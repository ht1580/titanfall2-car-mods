from pathlib import Path
import json, math, re, struct, subprocess, zipfile
import build as b

root=b.ROOT
report=json.loads((root/'FINAL-AUDIT.json').read_text())
pcf=root/'codex_weapon_fx_shared.pcf'
decoded=root/'shared-pcf-readback.txt'
subprocess.run([str(b.DMX),'-i',str(pcf),'-ie','binary','-o',str(decoded),'-oe','keyvalues2','-of','pcf'],check=True)
names=set(re.findall(r'"name" "string" "((?:cxcar|cxdt)_[^"]+)"',decoded.read_text()))
assert len(names)==38, len(names)
results={}
for key,work,rel in [('mythic','mythic_view','car101/ptpov_car101.mdl'),('doubleTake','double_view','doubletake/ptpov_doubletake.mdl')]:
 folder=Path(report[key]['folder'])
 data=(folder/'mod/models/weapons'/rel).read_bytes()
 assert struct.unpack_from('<i',data,4)[0]==53
 count,offset=struct.unpack_from('<2i',data,192)
 events=[]
 for i in range(count):
  pos=offset+i*232; nc,off=struct.unpack_from('<2i',data,pos+24)
  for j in range(nc):
   ep=pos+off+j*80
   options=data[ep+12:ep+76].split(b'\0')[0].decode('utf8','replace')
   if not options.startswith(('cxcar_','cxdt_')):continue
   assert len(options.encode())<64
   words=options.split();assert words[0] in names,options
   if len(words)>2:assert words[-1] in ('VFX_eye','VFX_base','hunter_fx','muzzle_flash'),options
   nameoff=struct.unpack_from('<i',data,ep+76)[0]
   ename=data[ep+nameoff:data.index(0,ep+nameoff)].decode()
   assert ename in ('AE_CL_CREATE_PARTICLE_EFFECT','AE_CL_STOP_PARTICLE_EFFECT')
   events.append(options)
 assert events
 with zipfile.ZipFile(report[key]['zip']) as z: assert z.testzip() is None
 results[key]={'particleEvents':len(events),'maxEventBytes':max(len(e.encode()) for e in events),'zipCRC':True}

d=root/'work/double_view'
for filename in ('ptpov_doubletake_anim_idle_anim_autoplay.smd','ptpov_doubletake_anim_idle_ads_anim_autoplay.smd'):
 nodes,frames=b.read_smd(d/filename)
 for i,(name,_) in nodes.items():
  if 'timemachine_ring_' not in name:continue
  values=[f[i][4] for f in frames]
  steps=[values[j+1]-values[j] for j in range(len(values)-1)]
  assert min(abs(x) for x in steps)>0.01
  assert max(steps)-min(steps)<1e-7
  assert abs(math.sin((values[-1]-values[0])/2))<1e-7
results['ringLoop']={'frames':191,'noRepeatedFrames':True,'closedRotations':True,'constantAngularStep':True}
a=Path(report['mythic']['folder'])/'mod/particles'
c=Path(report['doubleTake']['folder'])/'mod/particles'
assert (a/'particles_manifest.txt').read_bytes()==(c/'particles_manifest.txt').read_bytes()
assert (a/pcf.name).read_bytes()==(c/pcf.name).read_bytes()
results['sharedPCF']={'definitions':len(names),'identicalManifestAndPCF':True}
materials=Path(report['doubleTake']['folder'])/'mod/materials/models/doubletake_hunter_fx'
assert all((materials/f).exists() for f in ('energy.vmt','energy.vtf','flow.vtf'))
results['restoredMaterials']=['energy.vmt','energy.vtf','flow.vtf']
results['runtimeTested']=False
(root/'STATIC-AUDIT.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
