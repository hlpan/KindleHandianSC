#utf-8
#找出字体文件所有支持的字符列表

from lxml import etree
import pickle
import os

font_charset_map={}

#如何kindle不支持的字符，从以下列表[从第2个开始]中选择
#key:字体文件 value:字体在ttx文件对应的cmap_format_
font_list=['big_font_heiti/STHeitiMedium.ttf',#kindle支持的
                'big_font_heiti/SourceHanSansSC-Medium.otf',#生僻字第1方案,思源字体覆盖也比较全面，而且字体比较漂亮，所以首先
                'big_font_heiti/方正中等线_GBK.TTF',#生僻字第2方案
                'big_font_heiti/TH-Hak-P2.ttf',#生僻字第3方案
                'big_font_heiti/TH-Hak-P0.ttf',#生僻字第4方案
                'big_font_heiti/TH-Tshyn-P2.TTF',#黑体不够，宋体来凑
                'big_font_heiti/TH-Tshyn-P1.TTF',
                'big_font_heiti/TH-Tshyn-P0.TTF',
                ]

for font in font_list:
    print(u'正在处理：%s'%(font))
    root=etree.parse(os.path.splitext(font)[0]+'.ttx')
    result=root.xpath('//map[@code]')

    charset=set()
    for elem in result:
        s = elem.get('code')
        ##if s=='0x29bd3':
        ##    print(s)
        s = s.lstrip('0x')
        if len(s)==0:
            continue
        if len(s)%2==1:
            s='0'+s
        charset.add(chr(int(s, 16)))
        #if len(s)==2:
        #    charset.add(chr(int(s, 16)))
        #else:
        #    b=bytearray(b'\\u0000')
        #    b[2]=ord(s[0])
        #    b[3]=ord(s[1])
        #    b[4]=ord(s[2])
        #    b[5]=ord(s[3])
        #    charset.add(b.decode('unicode_escape'))
    #print(len(result))
    print(len(charset))

    font_charset_map[font]=charset

f = open("heiti_font_char_list", 'wb')
pickle.dump(font_charset_map, f)

print("Kindle默认字体支持字数：", len(font_charset_map[font_list[0]]))

temp=set()
for key,charset in font_charset_map.items():
    temp=temp|charset

print("咱们的大字体支持字数：", len(temp))