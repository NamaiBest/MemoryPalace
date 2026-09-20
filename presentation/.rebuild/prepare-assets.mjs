import fs from 'node:fs/promises';import sharp from 'sharp';
const root='presentation/revised/assets/';
let html=await fs.readFile('presentation/.rebuild/elastic.html','utf8');
const svgs=html.match(/<svg\b[\s\S]*?<\/svg>/g)||[];const svg=svgs.find(x=>x.includes('elastic-logo-title'));if(svg)await fs.writeFile(root+'elastic.svg',svg);
for(const n of ['elastic','voloridge']){await sharp(root+n+'.svg').resize({width:1000}).png().toFile(root+n+'.png');}
console.log('LOGOS READY');
