#-*- coding:utf-8 -*-
from lxml import html
from lxml import etree
import os
import re
import pickle

out_dir='E:\\My_HanDian'
base_dir='E:\\BaiduYunDownload\\handian\\zd'
dir_list=["zi","zi2","zi3","zi4","zi5","zi6"]
font_charset_map=pickle.load(open('D:/dev_ebook/epub_filter/font_char_list', 'rb'))
kindle_charset=font_charset_map['kindle_build_in/STSongMedium.ttf']

word_without_content=[]
non_standard_html=[]
def get_content(file_name):
    with open(file_name, 'r', encoding='utf-8') as f:
        data = f.read()
    word = re.findall(r'<title>字典中[\s]*([\S])[\s]*字的解释</title>', data)[0]
    if word not in kindle_charset:
        return [word, '']
    jb=re.findall(r'<DIV class="tab-page" id="jb">[\s\S\n]*?<\/DIV>', data)
    xx = re.findall(r'<DIV class="tab-page" id="xx">[\s\S\n]*?<\/DIV>', data)
    if len(jb):
        content=jb[0]
    #elif len(xx):#TODO现在只处理简单解释，以后再把各种解释都加入
    #    #如果没有“基本解释”,查找“详细解释”
    #    content=xx[0]
    else:
        #如果都没有，那就不要了
        word_without_content.append(word)
        content=''

    #content=re.sub(r'H2 class="tab"', r'H2 class="tab"', content)
    #content=re.sub(r'&nbsp;[\s\S]*?<',r'<', content)
    #给属性加上引号
    content=re.sub(r'class=([a-zA-Z0-9_-]+)',r'class="\g<1>"', content)
    content=re.sub(r'id=([a-zA-Z0-9_-]+)',r'id="\g<1>"', content)
    content=re.sub(r'TARGET=_blank',r'TARGET="_blank"', content)
    #标签改成小写
    content=re.sub(r'<(\w+)',lambda m: m.group(0).lower(), content)
    content=re.sub(r'</(\w+)',lambda m: m.group(0).lower(), content)
    if len(content):
        try:
            word_root =html.fromstring(content)
        except etree.Error as e:
            print(e)
            print(file_name)
            non_standard_html.append(file_name)
    return [word, content]

word_conten_map={}


def make_sub_elem(parent, tag, attrib={},_text=None):
    child=html.Element(tag,attrib)
    child.text=_text
    parent.append(child)
    return child

def get_pure_string(element):
    str_list=[]
    str_list.append(element.text)
    for child in element.getchildren():
        str_list.append(get_pure_string(child))
        str_list.append(child.tail)
    return ''.join(s for s in str_list if s)

def parse_ziyi(elem_list, start, end):
    #elem_list是指当前单词对应的所有子节点
    #start,end当前字义块的开始和结束位置
    #start+2是这个字本身，+3是它的拼音，[+4，)是解释
    #也有可能start+2是这个字本身，+3是它的一种其他写法，+4是它的拼音，[+5，)是解释
    #还有一种是没有拼音的
    parsed_ziyi={}
    word=''
    py_text=''
    sense=[]
    if len(elem_list[start+3].find_class('dicpy')):
        #字本身
        word=get_pure_string(elem_list[start+2]).strip()
        #拼音
        py_text=elem_list[start+3].getchildren()[0].text.strip()
        
        for i in range(start+4, end):
            text=get_pure_string(elem_list[i]).strip()
            text1=re.sub(r'\d+\.',r'',text).strip()
            if(text==text1):
                pass
            sense.append(text1)
           

    elif elem_list[start+3].find('strong') is not None:
        #字本身
        word=get_pure_string(elem_list[start+2])+get_pure_string(elem_list[start+3])
        #拼音
        py_text=elem_list[start+4].getchildren()[0].text.strip()
        for i in range(start+5, end):
            text=get_pure_string(elem_list[i]).strip()
            sense.append(text[text.find('.')+1:].strip())
        
    else:
        #这种是没有拼音和其它写法的，是一些生僻字
        word=get_pure_string(elem_list[start+2])
        #没有拼音
        py_text=''
        for i in range(start+3, end):
            text=get_pure_string(elem_list[i]).strip()
            sense.append(text[text.find('.')+1:].strip())

    word=re.sub(r'●', r'', word)
    parsed_ziyi['zi']=word.strip()#字本身

    parsed_ziyi['py'] = ' '.join(py_text.split())
    parsed_ziyi['jieshi']=sense
    return parsed_ziyi
def parse_word_jiben(content, parsed_word):
    word_root = html.fromstring(content)
    
    #所有字义的开始位置，由于字义是一个接一个的，
    #所以只需要在其结束位置加一个最len(children)就可以找到所有的字义内容
    pos=[]
    children=word_root.getchildren()
    for i,child in enumerate(children):
        #先找到“基本字义”行和“其它字义”来定位
        if len(child.getchildren()) \
        and child.getchildren()[0].tag == 'strong' and child.getchildren()[0].text\
        and ''.join(child.getchildren()[0].text.split()) in ['基本字义','基本字義','其它字义','其它字義']:
            pos.append(i)
    pos.append(len(children))
    
    if(len(pos)==1):
        return False

    for i in range(len(pos)-1):
        parsed_word.append(parse_ziyi(children, pos[i], pos[i+1]))

    return True


map_file_name=os.path.join(base_dir,'word_content_map')
try:
    with open(map_file_name, 'rb') as f:
        word_conten_map=pickle.load(f)
except IOError as e:
    for directory in dir_list:
        path_dir=os.path.join(base_dir,directory)
        files= os.listdir(path_dir) #得到文件夹下的所有文件名称
        for file in files:
            if os.path.splitext(file)[1]=='.htm': #判断是否是文件夹，不是文件夹才打开
                [word, content] = get_content(os.path.join(path_dir, file))
                word_conten_map[word]=content
    f = open(map_file_name, 'wb')
    pickle.dump(word_conten_map, f)
    print("有：",len(word_without_content), "个字无简单解释")

html_root=html.Element('html')
head=html.Element('head')
meta=html.Element('meta')
meta.set('http-equiv',"content-type")
meta.set('content',"text/html; charset=utf-8")
head.append(meta)
html_root.append(head)
body=html.Element('body')
html_root.append(body)
div=html.Element('div')
body.append(div)
p=html.Element('p')
div.append(p)
p.append(html.Element('img', src="images/cover.png", width="100%", height="100%", alt="cover"))
body.append(html.Element('mbp:pagebreak'))

make_sub_elem(body, 'p', _text="汉典kindle特别版")
body.append(html.Element('br'))
make_sub_elem(body, 'p', _text="只包含了Kindle内置字库中的词条")
body.append(html.Element('br'))
make_sub_elem(body, 'p', _text="版权信息")
make_sub_elem(body, 'p', _text="© hlpan 2019")
body.append(html.Element('mbp:pagebreak'))

body.append(html.Element('a',id="filepos1"))
dict_root=html.Element('mbp:frameset')
body.append(dict_root)
#with open(os.path.join(base_dir,'dictdd1.html'),'wb+') as f:
#    f.write(etree.tostring(html_root, encoding='utf-8', pretty_print=True, method='html'))


dict_root.append(html.Element("hr"))
print(*non_standard_html, sep = "\n")
word_cnt=0
for word,content in word_conten_map.items():
    #对于一个正常的文字
    parsed_word=[]
    if len(content) and parse_word_jiben(content, parsed_word):
        word_cnt+=1
        entry=html.Element("idx:entry", scriptable='yes')
        dict_root.append(entry)
        entry.append(html.Element("idx:orth",value=word))
        for parsed_ziyi in parsed_word:
            #首先展示单词
            b=html.Element('b')
            entry.append(b)
            #基本解释：homo_no='1',详细解释：homo_no='2'
            #make_sub_elem(b, 'word', {"homo_no":"1"}, parsed_ziyi['zi'])
            make_sub_elem(b, 'word', _text= parsed_ziyi['zi'])
            #拼音
            make_sub_elem(entry, 'phonetic', _text=parsed_ziyi['py'])
        
            entry.append(html.Element('br'))
            category=html.Element('category')
            entry.append(category)
            
            if len(parsed_ziyi['jieshi'])==1:
                #只有一条解释的情况
                sense=html.Element('sense')
                category.append(sense)
                #解释
                make_sub_elem(sense, 'description',_text=parsed_ziyi['jieshi'][0])
                category.append(html.Element('br'))
            else:
                for i, desc in enumerate(parsed_ziyi['jieshi']):
                    #每一个解释
                    sense=html.Element('sense')
                    category.append(sense)
                    #标号
                    make_sub_elem(sense, 'b', _text=str(i+1)+'.')
                    #解释
                    make_sub_elem(sense, 'description',_text=desc)
                    category.append(html.Element('br'))
            make_sub_elem(dict_root,'hr')

#使用etree的tostring函数才可以输出<br/>这样的
#使用html.tostring只能输出<br>
with open(os.path.join(out_dir,'HandianSC.html'),'wb+') as f:
    f.write(etree.tostring(html_root, encoding='utf-8', pretty_print=True, method='html'))

print("一共有：",word_cnt,"个字。")