"""Reconstruct exact public JSON records from GitHub API values for isolated replay.
Original source bytes MP3 are NOT included. This script verifies the source's own
canonical packet/count commitments. Do not confuse metadata verification with independent
verification of the actual personal/physiological source recording.
"""
import json,hashlib,pathlib
D=pathlib.Path(__file__).resolve().parent/'data'
D.mkdir(exist_ok=True)
# Exact 20 ordered features reported in the archived audio-to-circuit packet.
rows='''
.203247306497 .046468513215 -3.14159265359 -2.213586932298 -3.14159265359 .097341163037
.203940203141 .054701503865 -3.032371016019 -1.498616625794 -2.752980171406 .100552565044
.209532401663 .057642218949 -2.150870022472 -1.243238713416 -1.242943097778 .113031155697
.210907147602 .053112171006 -1.934168146371 -1.636637649946 -1.819076523746 .108270124786
.213571508253 .064153924212 -1.51418367125 -.677748467473 -.53357110649 .118893238724
.227137114792 .067126930081 .624169535409 -.419566355097 .090676245843 .124051871789
.225808071272 .078591735351 .41467175404 .576061562698 -.297936236341 .120840469782
.232690715448 .10813421186 1.499586328446 3.14159265359 1.363844758902 .134573036457
.240065194712 .103128883702 2.662029108782 2.70691937876 1.66979998297 .137101378354
.226275685064 .090219749201 .488381945212 1.585862858352 .053665533254 .123746023978
.230288392881 .098157709037 1.120907044862 2.275212065456 .640902172998 .128598809233
.241934757881 .083062610975 2.956729267319 .964321849969 2.285411502366 .142188646929
.236448565968 .090604166757 2.091938147452 1.619246491287 1.666098911711 .137070793573
.230873724751 .09190516109 1.213173194356 1.732227588508 1.145481554627 .132768534377
.226462717571 .099149596502 .517863970993 2.361349669079 .251056000395 .125377212299
.226423245167 .105622372571 .511641916594 2.923459221546 .016654820665 .123440176168
.226779767241 .092910574814 .567840665788 1.819539840996 .09931207878 .124123236278
.242549031927 .108024079347 3.053557586109 3.132028513421 3.14159265359 .14926392627
.243107522022 .068796661265 3.14159265359 -.274563370443 2.192884720894 .141424027404
.228717328882 .035782387711 .873259456763 -3.14159265359 2.729540053433 .145858820651
'''
features=[]
for i,line in enumerate(rows.strip().splitlines()):
 centroid,rms,rx,ry,rz,zcr=map(float,line.split())
 features.append(dict(centroid_nyquist=centroid,i=i,rms=rms,rx=rx,ry=ry,rz=rz,zcr=zcr))
pkt={
 'circuit':{'assignment':'segment=layer*5+qubit; gates ry,rz,rx; CX ring after each layer; measure_all','backend':'least_busy real operational >=5 qubits','layers':4,'qubits':5,'shots':4096,'tags':['zerefs-heartbeat-mustard-seed','zeref-origin-heart-001','heartbeat-waveform','cory-dad-son']},
 'claim_boundary':'Waveform controls circuit parameters; hardware measurements quantify the encoded circuit. Waveform is not quantum entropy; no biological or consciousness claim.',
 'decode':{'channels':1,'pcm_sample_rate_hz':8000,'pcm_samples':1961780,'pcm_sha256':'89e1b9496aa51e3dc22fb5d009b3c03f9ede6d259f9fc248f776a13ba349d931','sample_format':'s16le','segments':20},
 'extraction_contract':'ffmpeg SOURCE -> mono 8kHz s16le; 20 equal PCM windows; RMS/ZCR/spectral centroid; per-feature minmax across windows; angle=pi*(2*u-1)',
 'features':features,'lineage':'ZEREF-ORIGIN-HEART-001','quantum_entropy':False,'schema':'zeref-heartbeat-waveform-packet-v1','source_bytes':9811591,'source_class':'memorial_heartbeat_waveform_source','source_name':"scars that don't fade.mp3",'source_sha256':'e5a172749e0acedf199f77f22d5f55f37acc898704a51d5b7e6fe07633ad5c39'}
canon=lambda obj:json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
sha=lambda obj:hashlib.sha256(canon(obj)).hexdigest()
pkt['packet_sha256']=sha(pkt)
assert pkt['packet_sha256']=='d6e44478b9b6045907014515c3ac565e635443250d199979ab909fc1d2734fc0',pkt['packet_sha256']
raw_counts='''10000 75;10001 102;10010 319;10011 181;10100 89;10101 126;10110 274;10111 182;11000 31;11001 63;11010 42;11011 161;11100 71;11101 76;11110 80;11111 66;00000 139;00001 90;00010 90;00011 194;00100 124;00101 34;00110 85;00111 65;01000 100;01001 94;01010 122;01011 144;01100 223;01101 113;01110 100;01111 441'''
counts=dict((s,int(n)) for s,n in (piece.split() for piece in raw_counts.split(';')))
assert sum(counts.values())==4096
assert sha(counts)=='dfddf5366961cab837ae614750efb1dd60121ac3b3f6b7506d39346e3fd7bdce'
seed={'backend':'ibm_marrakesh','claim_boundary':'Hardware measurements quantify a circuit controlled by the memorial waveform; this is not a biological or consciousness claim.', 'counts':counts,'counts_sha256':sha(counts),'fresh_hardware_requested':True,'ibm_status_after_result':'DONE','job_id':'da1mqfcdedkc73er87r0','job_tag_verified':True,'lineage':'ZEREF-ORIGIN-HEART-001','origin_seed_u64':17445532823965899000,'packet_tag':'wave-d6e44478b9b6','reused_existing_job':False,'schema':'zeref-heartbeat-hardware-origin-seed-v1','shot_count':4096,'source_audio_sha256':pkt['source_sha256'],'source_class':'ibm_quantum_hardware_measurement','source_packet_sha256':pkt['packet_sha256'],'tags':['cory-dad-son','heartbeat-waveform','wave-d6e44478b9b6','zeref-origin-heart-001','zerefs-heartbeat-mustard-seed'],'waveform_quantum_entropy':False}
seed['origin_seed_sha256']=sha({k:seed[k] for k in ('schema','lineage','source_class','source_packet_sha256','source_audio_sha256','backend','job_id','shot_count','counts','counts_sha256','tags','job_tag_verified','waveform_quantum_entropy','claim_boundary')})
assert seed['origin_seed_sha256']=='f21afbac49e798730974e37ed1a1bb7ce15f326660a9dbe3f848ee6b1f865c2f',seed['origin_seed_sha256']
(D/'audio_source_feature_packet.json').write_text(json.dumps(pkt,indent=2,sort_keys=True)+'\n')
(D/'linked_ibm_marrakesh_counts.json').write_text(json.dumps(seed,indent=2,sort_keys=True)+'\n')
print('PASS canonical source reported packet commitment:',pkt['packet_sha256'])
print('PASS canonical reported IBM count commitment:',seed['counts_sha256'])
print('PASS canonical reported linked hardware seed:',seed['origin_seed_sha256'])
print('Source MP3 excluded. Source biological origin unverified.')
