import fs from 'node:fs/promises';import sharp from 'sharp';
const p='presentation/revised-v2/assets/person.svg';const svg=(await fs.readFile(p,'utf8')).replace('currentColor','#5A5D59');await sharp(Buffer.from(svg)).resize(400,400).png().toFile('presentation/revised-v2/assets/person.png');
