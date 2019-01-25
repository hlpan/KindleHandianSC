import os
from lxml import etree
from FilterHtml import FilterHtml
out_dir='D:/KindleHandian/KindleHandianSC/src/'
filter_html= FilterHtml('font_images',os.path.join(out_dir,'KindleHanDianSC.html'))
filter_html.run()
with open(os.path.join(out_dir,'KindleHanDianSCP.html'),'wb') as f:
    f.write(etree.tostring(filter_html.html_tree, encoding='utf-8', pretty_print=True, method='html'))
    f.close()

with open(os.path.join(out_dir,'manifest.txt'),'wb') as f:
    f.write(etree.tostring(filter_html.manifest, encoding='utf-8', pretty_print=True, method='html'))
    f.close()