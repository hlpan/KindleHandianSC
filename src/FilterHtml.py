# -*- coding: UTF-8 -*-
##########################################################
#从Html中找出生僻字并替换成图片

import pygame
from lxml import etree
from lxml import html
import re
import os
import pickle
import pygame.freetype
import pygame


class FilterHtml:
    'find all uncommon words in a html file and convert them to images'

    font_list=['big_font_heiti/STHeitiMedium.ttf',#kindle支持的
                'big_font_heiti/SourceHanSansSC-Medium.otf',#生僻字第1方案,思源字体覆盖也比较全面，而且字体比较漂亮，所以首先
                'big_font_heiti/方正中等线_GBK.TTF',#生僻字第2方案
                'big_font_heiti/TH-Hak-P2.ttf',#生僻字第3方案
                'big_font_heiti/TH-Hak-P0.ttf',#生僻字第4方案
                'big_font_heiti/TH-Tshyn-P2.TTF',#黑体不够，宋体来凑
                'big_font_heiti/TH-Tshyn-P1.TTF',
                'big_font_heiti/TH-Tshyn-P0.TTF',
                ]
    font_charset_name='heiti_font_char_list'


    def __init__(self, _image_dir, _html_file=None, _html_tree=None, _with_css=False):
        if _html_tree is not None:
            self.html_tree = _html_tree
            self.html_file=''
        elif _html_file is not None:
            self.html_tree=html.parse(_html_file)
            self.html_file=_html_file
        else:
            ValueError("Should input _html_file or _html_tree")
        #字体渲染器
        pygame.freetype.init()
        #key:字体名 value渲染器
        self.fonts_render = {}
        for font in FilterHtml.font_list[1:]:
            self.fonts_render[font]=pygame.freetype.Font(font, 50)
            if 'Medium' not in font:
                #对于没有自带加粗的字体进行适当的加粗
                #更加适合kindle的屏幕
                self.fonts_render[font].strong=True
                self.fonts_render[font].strength=1/36#default is 1/36 and the "bold" is 1/12
        #所有kindle目前支持的字符集合
        #'kindle内置中文字体/STHeitiMedium'
        self.font_charset_map=pickle.load(open(FilterHtml.font_charset_name, 'rb'))
        #kindle支持的字符集
        self.kindle_charset=self.font_charset_map[FilterHtml.font_list[0]]

        #生僻字和它对应的图片名
        self.char_image_map={}
       
        self.font_image_dir=_image_dir
        self.with_css=_with_css
        if self.with_css:
            self.new_css_filename='uncommon_word.css'
            with open(self.new_css_filename,'w') as css_file:
                css_file.write('''
                .image_as_font {
                    vertical-align: -0.15em;
                    width: 1em;
                    height: 1em;
                    margin: 0.05em;
                    }
                ''')
                css_file.close()

        if not os.path.exists(self.font_image_dir):
            os.makedirs(self.font_image_dir)
        #生成图片的列表文件
        self.manifest=etree.Element('manifest')
    def run(self):
        build_text_list = etree.XPath("//text()")
        text_list=build_text_list(self.html_tree)
       
        rel_image_dir=self.font_image_dir
        for text in text_list:
            #找出一段文字中生僻字的位置
            pos_list = self.find_uncommon_words_in_one_text(text)
            self.add_image_tag_for_uncommon_words_in_one_text(text, pos_list,rel_image_dir)

   
    def find_uncommon_words_in_one_text(self, text):
        #找出一段文字中生僻字的位置
        #并渲染从生僻字到png图片
        pos_list=[]
        for idx,char in enumerate(text):
            if re.match(r'\s', char):
                continue
            if char not in self.kindle_charset:
                pos_list.append(idx)
                #没有生成图片时才重新生成
                if char not in self.char_image_map:
                    is_in_big_font=False
                    #查找char所在的字体并渲染，big font还是不够大啊
                    for font, render in self.fonts_render.items():
                        if char in self.font_charset_map[font]:
                            #(surface, textpos) = render.render(char, (0, 0, 0))
                            surface=pygame.Surface((50,50))
                            surface.fill((255,255,255))
                            self.render_word(surface, char, render)
                            b=char.encode("unicode_escape")
                            name = str(b[2:])[2:-1]
                            name+=".jpeg"
                            pygame.image.save(surface, os.path.join(self.font_image_dir,name))
                            data=open(os.path.join(self.font_image_dir,name),'rb').read()
                            self.manifest.append(etree.Element('item',{ 'id':str(b[2:])[2:-1],'href':self.font_image_dir+'/'+name,'media-type':"image/jpep"}))
                            self.char_image_map[char]=name
                            is_in_big_font=True
                            break
                    if not is_in_big_font:
                        print("Very very uncommon: ",char)
        return pos_list

    def add_image_tag_for_uncommon_words_in_one_text(self, text, pos_list, rel_image_dir):
        #插入每个生僻字对应的item
        #text当前处理的文本
        #post_list:已经找出的生僻字的位置
        #image_dir:生成的图片相对于当前html所在的目录
        if len(pos_list):
            parent=text.getparent()
            if not text.is_tail:
                parent.text=text[0:pos_list[0]]
                pos_list.append(len(text))
                for i in range(len(pos_list)-1):
                    item = text.getparent().makeelement("img")
                    the_uncommon_char = text[pos_list[i]]
                    try:
                        item.set('src', rel_image_dir+'/'+self.char_image_map[the_uncommon_char])
                        if self.with_css:
                            item.set('class','image_as_font')
                        else:
                            item.set('width','25')
                            item.set('height','25')
                        #item.text ='|'+text[pos_list[i]]+'|'
                        parent.insert(i, item)
                    except KeyError:
                        print(text)
                    item.tail=text[pos_list[i]+1:pos_list[i+1]]
            else:
                pos_list.insert(0,-1)
                for i in range(len(pos_list)-1):
                    item = text.getparent().makeelement("img")
                    the_uncommon_char = text[pos_list[i+1]]
                    try:
                        item.set('src', rel_image_dir+'/'+self.char_image_map[the_uncommon_char])
                        if self.with_css:
                            item.set('class','image_as_font')
                        else:
                            item.set('width','25')
                            item.set('height','25')
                    except KeyError:
                        print(text)
                    #item.text ='|'+text[pos_list[i+1]]+'|'
                    parent.addnext(item)
                    #lxml的addnext操作会删除tail，所以需要后设置
                    parent.tail=text[pos_list[i]+1:pos_list[i+1]]
                    parent=item
                parent.tail=text[pos_list[-1]+1:]

    def render_word(self, surf, word, font, color=(0, 0, 0)):
        width, height = surf.get_size()
        bounds = font.get_rect(word)
        x,y=(width-bounds.width)/2,(height-bounds.height)/2
        font.render_to(surf, (x, y), word, color)
        #if x>0 and y>0 :
        #    font.render_to(surf, (x, y), word, color)
        #else:
        #    surf,textpos=font.render(word, color)
