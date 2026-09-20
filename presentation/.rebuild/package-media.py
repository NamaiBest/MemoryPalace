from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E
import subprocess
B=Path(__file__).resolve().parent; A=B.parent/'revised/assets'
for kind,durations in [('baseline',[3,3,4]),('persistence',[1.5,1.5,1.5,1.5,3])]:
    listing=B/(kind+'.concat')
    listing.write_text(''.join(f"file '{B}/{kind}-{i}.png'\nduration {d}\n" for i,d in enumerate(durations))+f"file '{B}/{kind}-{len(durations)-1}.png'\n")
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(listing),'-t',str(sum(durations)),'-r','24','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(A/(kind+'-explainer.mp4'))],check=True)
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
R='http://schemas.openxmlformats.org/package/2006/relationships'; CT='http://schemas.openxmlformats.org/package/2006/content-types'
with ZipFile(B/'candidate-base.pptx') as z: files={n:z.read(n) for n in z.namelist()}
for num,kind,video,poster in [(2,'intro',A/'MemoryPalace-36s.mp4',A/'film-poster.png'),(6,'baseline',A/'baseline-explainer.mp4',B/'baseline-2.png'),(7,'persistence',A/'persistence-explainer.mp4',B/'persistence-4.png')]:
    slidekey=f'ppt/slides/slide{num}.xml'; relkey=f'ppt/slides/_rels/slide{num}.xml.rels'
    root=E.fromstring(files[slidekey]); rel=E.fromstring(files[relkey]); tree=root.find('p:cSld/p:spTree',ns)
    if num==2:
        for pic in list(tree.findall('p:pic',ns)): tree.remove(pic)
    ident=max([int(v) for v in root.xpath('//@id') if v.isdigit()]+[1])+1
    ids=[f'rIdMemoryVideo{num}',f'rIdMemoryMedia{num}',f'rIdMemoryPoster{num}']
    for rid,typ,target in [(ids[0],ns['r']+'/video',f'../media/{kind}.mp4'),(ids[1],'http://schemas.microsoft.com/office/2007/relationships/media',f'../media/{kind}.mp4'),(ids[2],ns['r']+'/image',f'../media/{kind}-poster.png')]:
        E.SubElement(rel,'{'+R+'}Relationship',Id=rid,Type=typ,Target=target)
    pic=E.fromstring(f'''<p:pic xmlns:p="{ns['p']}" xmlns:a="{ns['a']}" xmlns:r="{ns['r']}"><p:nvPicPr><p:cNvPr id="{ident}" name="{kind} video"><a:hlinkClick action="ppaction://media"/></p:cNvPr><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr><a:videoFile r:link="{ids[0]}"/><p:extLst><p:ext uri="{{DAA4B4D4-6D71-4841-9C94-3DE7FCFB9230}}"><p14:media xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main" r:embed="{ids[1]}"/></p:ext></p:extLst></p:nvPr></p:nvPicPr><p:blipFill><a:blip r:embed="{ids[2]}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="18288000" cy="10287000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>''')
    tree.append(pic)
    files[slidekey]=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True); files[relkey]=E.tostring(rel,xml_declaration=True,encoding='UTF-8',standalone=True)
    files[f'ppt/media/{kind}.mp4']=video.read_bytes();files[f'ppt/media/{kind}-poster.png']=poster.read_bytes()
ct=E.fromstring(files['[Content_Types].xml'])
if not ct.xpath('//*[local-name()="Default"][@Extension="mp4"]'):E.SubElement(ct,'{'+CT+'}Default',Extension='mp4',ContentType='video/mp4')
files['[Content_Types].xml']=E.tostring(ct,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(B/'candidate-media.pptx','w',ZIP_DEFLATED) as z:
    for n,b in files.items():z.writestr(n,b)
print('Packaged three embedded movies')
