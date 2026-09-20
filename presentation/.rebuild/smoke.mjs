import fs from 'node:fs/promises';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
const p=Presentation.create({slideSize:{width:1920,height:1080}});const s=p.slides.add();s.background.fill='#F3EFE6';const t=s.shapes.add({geometry:'textbox',position:{left:100,top:100,width:1500,height:200},fill:'none',line:{fill:'none',width:0}});t.text='Memorypalace';t.text.style={typeface:'Poppins',fontSize:86,color:'#171714',bold:true,autoFit:'none',insets:{left:0,right:0,top:0,bottom:0}};
const b=await p.export({slide:s,format:'png',scale:.5});await fs.writeFile('presentation/.rebuild/smoke.png',new Uint8Array(await b.arrayBuffer()));console.log('RENDER OK');
