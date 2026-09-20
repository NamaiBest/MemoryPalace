from pathlib import Path
old=Path('presentation/.rebuild/build-deck.mjs').read_text()
s=old.replace("presentation/.rebuild","presentation/.revision-v2").replace("const F='Poppins';","const V=path.join(ROOT,'presentation/revised-v2/assets');\nconst F='Poppins';")
s=s.replace('design/branding/memorypalace-connected-flow-v1.png','design/branding/variants/01-clean.png')
start=s.index('// 2 —')
s=s[:start]+'''// Opening question, before the film.
s=slide('', '', 'Open with an everyday lapse in recall, not a medical claim. This is a relatable motivation, not evidence that an EEG detector identifies forgetting. Transition to the concept film.');
text(s,'Ever walked into a room…',110,230,1650,145,90,C.ink,true);
text(s,'and forgotten what you came to say?',110,408,1660,210,82,C.ink,true);
text(s,'What if the context was still there when you needed it?',110,768,1630,130,43,C.blue);
''' +s[start:]
start=s.index('// 3 —');end=s.index('// 4 —')
s=s[:start]+'''// Reflection follows the film.
s=slide('Come back to your day','Revisit what happened. Learn from it. Let someone close understand.','At the end of the day, revisit selected recordings and their context. Reflection is a user activity, not a clinical assessment. The implemented Share flow drafts a personal note from selected moments; the user chooses the recipient, reviews the draft and shares it. Do not assert end-to-end encryption or a privacy guarantee that is not implemented. Source: app/components/share/SharePage.tsx.');
await img(s,path.join(A,'share.png'),110,345,1020,575);
text(s,'Reflect',1210,350,590,70,46,C.blue,true);text(s,'What happened?\\nWhat do I want to learn?',1210,432,580,105,34,C.muted);
text(s,'Share with someone close',1210,608,600,115,44,C.ink,true);text(s,'Help them understand the moments\\nthat stayed with you.',1210,722,590,110,33,C.muted);
text(s,'Deeply personal context. You choose what to share.',110,970,1690,75,37,C.gold,true);
''' +s[end:]
# Replace hardware layout with actual Crown reference.
start=s.index('flow(s,',s.index('// 4 —'));end=s.index('// 5 —')
s=s[:start]+'''await img(s,path.join(V,'crown.png'),110,350,730,515);
text(s,'Neurosity Crown',150,888,650,70,40,C.ink,true,'center');
text(s,'Sense',980,365,750,65,43,C.blue,true);text(s,'EEG compared with your personal baseline',980,433,800,82,32,C.muted);
text(s,'Capture context',980,554,750,65,43,C.gold,true);text(s,'Ray-Ban Meta glasses: the wearable camera concept',980,623,800,88,32,C.muted);
text(s,'Revisit',980,753,750,65,43,C.ink,true);text(s,'Search, reflect, and share in Memorypalace',980,822,800,88,32,C.muted);
''' +s[end:]
# Add waveform/head calibration diagram before existing baseline explanation.
start=s.index('// 6 —')
s=s[:start]+'''// Three wearers: raw range is an illustration; theta/alpha remains the implemented trigger.
s=slide('Start by learning your normal','First-time calibration gives each wearer a personal reference.','The three raw EEG traces and 20 / 40 / 70 microvolt ranges are synthetic illustrations, not measured people or diagnostic norms. Peak-to-peak means maximum minus minimum; raw amplitude also depends on recording conditions. The live prototype calibrates theta/alpha mean and spread over 120 seconds, then uses a z-score. It does not trigger from raw peak-to-peak amplitude. Person icon: Lucide user-round, https://github.com/lucide-icons/lucide/blob/main/icons/user-round.svg (ISC).');
for(let i=0;i<3;i++){
 const x=110+i*570, amp=[10,20,35][i],col=[C.blue,C.gold,C.green][i];
 const raw=Array.from({length:65},(_,j)=>Math.sin(j*.77)+.3*Math.sin(j*2.13));const lo=Math.min(...raw),hi=Math.max(...raw);const values=raw.map(v=>((v-lo)/(hi-lo)*2-1)*amp);
 s.charts.add('line',{position:{left:x,top:335,width:535,height:280},categories:values.map((_,j)=>String(j)),title:'Wearer '+String.fromCharCode(65+i),titleTextStyle:{typeface:F,fontSize:33,fill:col,bold:true},series:[{name:'Illustrative raw EEG (µV)',values,line:{fill:col,width:3},marker:{symbol:'none'},valuesFormatCode:'0.0'}],hasLegend:false,chartFill:C.bg,plotAreaFill:C.bg,lineOptions:{smooth:false},xAxis:{visible:false},yAxis:{min:-40,max:40,numberFormatCode:'0',textStyle:{typeface:F,fontSize:20,fill:C.muted},majorGridlines:{fill:C.line,width:1}},chartLine:{fill:'none'},plotAreaLine:{fill:'none'}});
 await img(s,path.join(V,'person.png'),x+175,643,185,185);
 text(s,[20,40,70][i]+' µV peak-to-peak',x,849,535,60,35,col,true,'center');
}
text(s,'Different ranges. A baseline that belongs to you.',110,947,1700,65,40,C.ink,true);
note(s,'Illustrative raw EEG • peak-to-peak = highest minus lowest • trigger uses normalized theta/alpha activity');
''' +s[start:]
# Replace Meta with feature-to-model mappings.
start=s.index('// 11 —');end=s.index('// 12 —')
s=s[:start]+'''// Meta models mapped to actual app features.
s=slide('Meta powers context and connection','Understand a moment, ask about it, then share what matters.','Sponsor prompt: Bringing People Closer Together with AI. Muse Spark (muse-spark-1.3) is used in vision.py for recorded-video descriptions and in agent.py for Memory Guard reasoning/tool use and share_note generation. Muse Voice Transcribe (muse-voice-transcribe-1.0) transcribes push-to-talk input in voice.py; playback speech uses device speech synthesis. Muse Image and a Muse personal-agent connector are not implemented and are not claimed. Sources: hardware-demo/eegdemo/vision.py; agent.py; voice.py; app/components/share/SharePage.tsx. Sponsor links: https://developer.meta.com/ai/models/muse-spark/ and https://developer.meta.com/ai/models/muse-voice-transcribe/ .');
await img(s,path.join(A,'meta.png'),1430,70,350,125,'contain',{left:0,top:.26,right:0,bottom:.26});
const metaRows=[['Describe the moment','Muse Spark','Turns a recorded clip into a searchable description.'],['Talk to Memory Guard','Muse Voice Transcribe + Muse Spark','Transcribes your question, then reasons over retrieved moments.'],['Share with someone close','Muse Spark','Drafts a personal note from moments you select and review.']];
for(let i=0;i<3;i++){const y=350+i*210;text(s,metaRows[i][0],110,y,660,70,40,C.ink,true);text(s,metaRows[i][1],825,y,940,62,35,C.blue,true);text(s,metaRows[i][2],825,y+73,945,102,31,C.muted);if(i<2)line(s,110,y+181,1690);}
text(s,'Personal context becomes a way to connect.',110,993,1670,55,34,C.gold,true);
''' +s[end:]
# VoloRidge: replace outdated dataset story with two current technical slides.
start=s.index('// 12 —');end=s.index('// 13 —')
s=s[:start]+'''// VoloRidge approach and validation, from SLIDES-VOLORIDGE.md.
s=slide('84 numbers and a logistic regression','Voloridge • extracting sustained state changes from public EEG data','Voloridge asked for signal out of public data. Ours is EEG: 28 channels, five people, fifteen sessions from Shin et al. 2018 dataset A. Regress out eye-channel contributions, measure three band powers, logistic regression, one moving average. Alternatives were paired against their own baselines on the same recordings, windows and calibration folds. They lost or tied; these rows are not a cross-participant leaderboard. The one retained addition is a smoothing half-life. Source: presentation/SLIDES-VOLORIDGE.md and eeg-state-detection/README.md. Public-data research, distinct from the running four-window prototype detector.');
shape(s,1570,40,240,160,'#102F45');await img(s,path.join(A,'voloridge.png'),1580,43,220,150);
text(s,'The pipeline',110,339,740,65,42,C.blue,true);
const steps=[['28 EEG channels, 200 Hz','Shin et al. 2018 • five people, 15 sessions'],['Regress out eye channels','Fit before task; freeze before scoring'],['Theta / alpha / beta log power','84 features • 2-second windows, every 0.25 s'],['Logistic regression → moving average','Task versus rest • one smoothing parameter']];
for(let i=0;i<4;i++){let y=432+i*138;text(s,steps[i][0],110,y,830,62,34,C.ink,true);text(s,steps[i][1],110,y+57,830,66,28,C.muted);}
text(s,'More complexity did not win',1010,339,800,70,41,C.ink,true);
for(const [i,label,count] of [[0,'Riemannian tangent space','1,218 features'],[1,'26-bin Fourier spectrum','728 features'],[2,'Zigzag topology','108 features'],[3,'Bayesian state-space','Latent state'],[4,'Three more alternatives','Lost or tied']]){let y=435+i*73;text(s,label,1010,y,480,62,28,C.muted);text(s,count,1515,y,290,62,27,C.muted);}
line(s,1010,827,790,C.gold,3);text(s,'Band power + logistic',1010,858,785,67,40,C.ink,true);text(s,'84 features + one smoothing parameter',1010,931,790,68,30,C.gold,true);
note(s,'Paired comparisons against each method’s own baseline • source: eeg-state-detection/README.md');
s=slide('Does the signal survive a harder test?','Voloridge • models frozen before scoring held-out task blocks','Models were frozen and SHA-256 hashed before held-out blocks. Per session: first six blocks calibrate, last three score. The circular time-shift null preserves autocorrelation; shuffled windows would break it. 2,000 shifts per session. Eight of 15 sessions beat that null at nominal p ≤ 0.05 (session-wise, not multiplicity corrected). Orange diamonds are the identical pipeline on eye channels; two participants show substantial ocular contribution. The same null discipline rejected the brief-event zigzag result: 6/36 versus a 2/36 baseline, p=0.13 against random flags. Sources: eeg-state-detection/README.md; outputs/backtest_state/report.json; outputs/burst_diagnostic_dev/report.json. This is offline task/rest detection, not real-world forgetting or emotion accuracy.');
shape(s,1570,40,240,160,'#102F45');await img(s,path.join(A,'voloridge.png'),1580,43,220,150);
await img(s,path.join(ROOT,'eeg-state-detection/outputs/backtest_state/summary.png'),85,315,1750,649,'contain');
text(s,'Grey: random alignment of the same signal. 8 of 15 sessions beat it at p ≤ 0.05.',110,958,1690,57,29,C.ink,true);
line(s,110,1021,1690,C.gold,2);text(s,'Brief-event detector: 3× its baseline, but p = 0.13 against random flags — rejected.',110,1035,1700,42,25,C.gold,true);
''' +s[end:]
# Do not generate the superseded staged animations again.
s=s[:s.index('// Staged native chart')]+"console.log('DECK READY');\n"
Path('presentation/.revision-v2/build-deck.mjs').write_text(s)
