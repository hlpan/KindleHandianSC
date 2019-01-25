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
    if len(xx):
        content=xx[0]
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

def parse_form(elem_list, start, end):
    #详细解释里面的每一条都包含多个字形如：〈数〉
    #elem_list是指当前单词对应的所有子节点
    #start,end当前字义块的开始和结束位置
    # start是字+拼音
    
    parsed_form={}
    word=get_pure_string(elem_list[start]).strip()
    #一般来说start+1是字形类别，但也可能是没有字形的
    form=get_pure_string(elem_list[start+1]).strip()
    offset=0
    if not re.findall(r'〈\w〉|［\w］',form):
        offset=-1
        form=''
  
    #每个字形的解释是一列表
    #每一个元素sense又是一个字典，两个key：'sense','example'
    
    sense_list=[]
    for i in range(offset+start+2, end):
        text=get_pure_string(elem_list[i]).strip()
        if len(text)==0:
            continue
        if len(re.findall(r'^\(\d+\)', text)):
            sense={}
            sense_list.append(sense)
            sense['description']=re.sub(r'^\(\d+\)',r'', text)
            sense['example']=[]
        else:
            try:
                #如果text没有以(\d+)开始，那么它都是前一个sense的例句
                sense['example'].append(text)
            except UnboundLocalError:
                #如果sense没有初始化，那么这种形式是没有括号的解释
                sense={}
                sense_list.append(sense)
                sense['description']= text
                sense['example']=[]

    parsed_form['zi']=word
    parsed_form['xing']=form
    parsed_form['jieshi']=sense_list
    return parsed_form



def parse_ziyi_xiangxi(elem_list, start, end, word):
    #分析'详细字义'或'词性变化'，找到其中的字形如：〈数〉
    pos=[]
    parsed_ziyi=[]
    if word=='校':
        print(word)
    for i in range(start, end):
        if len(elem_list[i].getchildren()) \
            and elem_list[i].getchildren()[0].tag == 'strong' \
            and elem_list[i].getchildren()[0].text == word \
            and elem_list[i].find_class('dicpy'):
            pos.append(i)
    pos.append(end)

    if len(pos)==1:
        pass
    for i in range(len(pos)-1):
        #每种字义包括多个字形如：〈数〉
        parsed_ziyi.append(parse_form(elem_list, pos[i], pos[i+1]))

    return parsed_ziyi
def parse_word_xiangxi(wrod, content, parsed_word):
    word_root = html.fromstring(content)

    #所有字义的开始位置，由于字义是一个接一个的，
    #所以只需要在其结束位置加一个最len(children)就可以找到所有的字义内容
    pos=[]
    cat_names=[]
    children=word_root.getchildren()
    for i,child in enumerate(children):
        #先找到“基本字义”行和“其它字义”来定位
        if len(child.getchildren()) \
        and child.getchildren()[0].tag == 'strong' and child.getchildren()[0].text\
        and ''.join(child.getchildren()[0].text.split()) in ['详细字义','基本词义','词性变化','常用词组']:
            pos.append(i)
            cat_names.append(''.join(child.getchildren()[0].text.split()))

    pos.append(len(children))
    
    if(len(pos)==1):
        return False

    #每一个字包含'详细字义'或'词性变化'或'基本词义'三种分类
    #每一类又包含若干字形
    #每一个字形才是包含多条解释的字典项
    #所以每一个字的结果是一个dict={}有三项
    #'详细字义':[字形1，字形2，……]
    #'基本词义':[字形1，字形2，……]
    #'词性变化':[字形1，字形2，……]
    for i in range(len(pos)-1):
        cat=cat_names[i]
        if cat=='常用词组':
            continue
        parsed_word[cat]=[]
        parsed_word[cat].append(parse_ziyi_xiangxi(children, pos[i], pos[i+1], word))

    return True




map_file_name=os.path.join(base_dir,'word_content_map1')
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
make_sub_elem(head,'link',{'href':'HandianSC.css','rel':"stylesheet", 'type':"text/css"})
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
for word,content in word_conten_map.items():
    #对于一个正常的文字
    parsed_word={}
    if len(content) and parse_word_xiangxi(word, content, parsed_word):
        entry=html.Element("idx:entry", scriptable='yes')
        dict_root.append(entry)
        entry.append(html.Element("idx:orth",value=word))

        #对“详细解释”页面的每一类按'详细字义'，'基本词义'，'词性变化'的顺序显示
        
        cat_list=['详细字义','基本词义','词性变化']
        for cat in cat_list:
            try:
                parsed_cat=parsed_word[cat]
            except:
                continue
            for parsed_ziyi in parsed_cat:
                #parsed_ziyi包含若干字形，对于每一个字形
                for zixing in parsed_ziyi:
                    if 0==len(zixing['jieshi']):
                        continue
                    #首先展示单词
                    b=html.Element('b')
                    entry.append(b)
                    #基本解释：homo_no='1',详细解释：homo_no='2'
                    #make_sub_elem(b, 'word', {"homo_no":"1"}, parsed_ziyi['zi'])
                    make_sub_elem(b, 'word', _text= zixing['zi'])
                    make_sub_elem(b, 'span', _text= zixing['xing'])
                    entry.append(html.Element('br'))
                    category=html.Element('category')
                    entry.append(category)
                    
                    for i, desc in enumerate(zixing['jieshi']):
                        #每一个解释
                        sense=html.Element('sense')
                        category.append(sense)
                        #标号
                        make_sub_elem(sense, 'b', _text=str(i+1)+'.')
                        #解释
                        make_sub_elem(sense, 'description',_text=desc['description'])
                        if len(desc['example'])>10:
                            print("LLLLLLLL:", word)
                        for j,example in enumerate(desc['example']):
                            label=chr(ord('a')+j)
                            example=label+'. '+example
                            make_sub_elem(sense, 'example',{'class':'small'}, _text=example)
                        category.append(html.Element('br'))
                    make_sub_elem(dict_root,'hr')

#使用etree的tostring函数才可以输出<br/>这样的
#使用html.tostring只能输出<br>
with open(os.path.join(out_dir,'HanDianSC.html'),'wb+') as f:
    f.write(etree.tostring(html_root, encoding='utf-8', pretty_print=True, method='html'))