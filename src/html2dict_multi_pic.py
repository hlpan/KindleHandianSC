#-*- coding:utf-8 -*-
from lxml import html
from lxml import etree
import os
import re
import pickle

out_dir='.'
base_dir='E:\\BaiduYunDownload\\handian\\zd'
dir_list=["zi","zi2","zi3","zi4","zi5","zi6"]
font_charset_map=pickle.load(open('D:/dev_ebook/epub_filter/font_char_list', 'rb'))
kindle_charset=font_charset_map['kindle_build_in/STSongMedium.ttf']

word_without_content=[]
non_standard_html=[]


def get_content(file_name):
    #返回dict,key:word,value:content_map
    #content_map也是dict,key:基本解释or详细解释,value:字符串
    content_map={}
    with open(file_name, 'r', encoding='utf-8') as f:
        data = f.read()
    word = re.findall(r'<title>字典中[\s]*([\S])[\s]*字的解释</title>', data)[0]
    if word not in kindle_charset:
        return [word, content_map]
    #基本解释
    jb=re.findall(r'<DIV class="tab-page" id="jb">[\s\S\n]*?<\/DIV>', data)
    #详细解释
    xx = re.findall(r'<DIV class="tab-page" id="xx">[\s\S\n]*?<\/DIV>', data)
    #康熙字典
    kx = re.findall(r'<div id="kxnr">[\s\S\n]*?<\/div>', data)
    if len(jb):
        content_map['基本解释']=jb[0]
    else:
        content_map['基本解释']=''
    if len(xx):
        content_map['详细解释']=xx[0]
    else:
        content_map['详细解释']=''
    if len(kx):
        content_map['康熙字典']=kx[0]
    else:
        content_map['康熙字典']=''


    #content=re.sub(r'H2 class="tab"', r'H2 class="tab"', content)
    #content=re.sub(r'&nbsp;[\s\S]*?<',r'<', content)
    ##给属性加上引号
    #content=re.sub(r'class=([a-zA-Z0-9_-]+)',r'class="\g<1>"', content)
    #content=re.sub(r'id=([a-zA-Z0-9_-]+)',r'id="\g<1>"', content)
    #content=re.sub(r'TARGET=_blank',r'TARGET="_blank"', content)
    ##标签改成小写
    #content=re.sub(r'<(\w+)',lambda m: m.group(0).lower(), content)
    #content=re.sub(r'</(\w+)',lambda m: m.group(0).lower(), content)
    #if len(content):
    #    try:
    #        word_root =html.fromstring(content)
    #    except etree.Error as e:
    #        print(e)
    #        print(file_name)
    #        non_standard_html.append(file_name)
    return [word, content_map]

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

def parse_form(elem_list, start, end, word):
    #详细解释里面的每一条都包含多个字形如：〈数〉
    #elem_list是指当前单词对应的所有子节点
    #start,end当前字义块的开始和结束位置
    parsed_form={}
    
    # start是字+拼音，而且是以◎开头的
    zi_py=get_pure_string(elem_list[start]).strip()
    #start+1分为三类，  # 1:是字的一些其它写法# 2:是字形类别 # 2:（没有字形）是解释
    offset=0
    text=get_pure_string(elem_list[start+1]).strip()
    if len(elem_list[start+1].find_class('dicpy')):
        zi_py+=get_pure_string(elem_list[start+1])
    else:
        #如果不是其它写法，退回去再看看它是不是字形类别
        offset=offset-1

    text=get_pure_string(elem_list[offset+start+2]).strip()
    if re.findall(r'〈\w〉|［\w］',text):
        form=text
    else:
        #如果不是字形类别，退回去看看它是不是解释
        offset=offset-1
        form=''

   
    #每个字形的解释是一列表
    #每一个元素sense又是一个字典，两个key：'sense','example'
    
    sense_list=[]
    for i in range(offset+start+3, end):
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

    parsed_form['zi']=zi_py
    parsed_form['xing']=form
    parsed_form['jieshi']=sense_list
    return parsed_form



def parse_ziyi_xiangxi(elem_list, start, end, word):
    #分析'详细字义'或'词性变化'，找到其中的字形如：〈数〉
    pos=[]
    parsed_ziyi=[]
    
    for i in range(start, end):
        if len(elem_list[i].getchildren()) \
            and elem_list[i].getchildren()[0].tag == 'strong' \
            and elem_list[i].getchildren()[0].text == word \
            and len(re.findall(r'◎', elem_list[i].text)):
            pos.append(i)
    pos.append(end)

    if len(pos)==1:
        pass
    for i in range(len(pos)-1):
        #每种字义包括多个字形如：〈数〉
        parsed_ziyi.append(parse_form(elem_list, pos[i], pos[i+1], word))

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

def parse_word_kangxi(wrod, content, parsed_word):
    word_root = html.fromstring(content)
    children=word_root.getchildren()

    # 康熙字典的结构比较简单
    # 每个字有两个属性，jianjie,jieshi(list)
    jieshi=[]
    #children[0]是字的简介：【子集上】【一字部】七 ·康熙筆画：2　·部外筆画：1
    parsed_word['jianjie']=get_pure_string(children[0])
    #children[2]是字的图片展示，现在先不管它
    #children[4]是字的解释
    for i in range(1, len(children)):
        if children[i].tag=='p':
            jieshi.append(get_pure_string(children[i]))
    parsed_word['jieshi']=jieshi
    if len(jieshi)==0:
        return False
    return True

def parse_print_tab_jiben(dict_root, homo_no, word,content):
    parsed_word=[]
    if not (len(content) and parse_word_jiben(content, parsed_word)):
        return False
    #word_cnt+=1
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
    return True

def parse_print_tab_xiangxi(dict_root, homo_no, word, content):
    if word=='氍':
        print(word)
    parsed_word={}
    if not (len(content) and parse_word_xiangxi(word, content, parsed_word)):
        return False
    entry=html.Element("idx:entry", scriptable='yes')
    dict_root.append(entry)
    entry.append(html.Element("idx:orth",value=word))

    #对“详细解释”页面的每一类按'详细字义'，'基本词义'，'词性变化'的顺序显示

    cat_list=['详细字义','基本词义','词性变化']
    is_empty=True
    for cat in cat_list:
        try:
            parsed_cat=parsed_word[cat]
        except KeyError:
            continue
        for parsed_ziyi in parsed_cat:
            #parsed_ziyi包含若干字形，对于每一个字形
            for zixing in parsed_ziyi:
                if 0==len(zixing['jieshi']):
                    continue
                is_empty=False
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
                        #print("Too many: exaple", word)
                        pass
                    for j,example in enumerate(desc['example']):
                        label=chr(ord('a')+j)
                        example=label+'. '+example
                        make_sub_elem(sense, 'description',{}, _text=example)
                    category.append(html.Element('br'))
    if is_empty:
        return False
    make_sub_elem(dict_root,'hr')
    return True

def parse_print_tab_kangxi(dict_root, homo_no, word, content):
    parsed_word={}
    if not (len(content) and parse_word_kangxi(word, content, parsed_word)):
        return False
    entry=html.Element("idx:entry", scriptable='yes')
    dict_root.append(entry)
    entry.append(html.Element("idx:orth",value=word))

    #对“详细解释”页面的每一类按'详细字义'，'基本词义'，'词性变化'的顺序显示
    #首先展示单词
    b=html.Element('b')
    entry.append(b)
    #基本解释：homo_no='1',详细解释：homo_no='2'
    #make_sub_elem(b, 'word', {"homo_no":"1"}, parsed_ziyi['zi'])
    make_sub_elem(b, 'word', _text= word)
    entry.append(html.Element('br'))
    category=html.Element('category')
    entry.append(category)
    
    sense=html.Element('sense')
    category.append(sense)
    make_sub_elem(sense, 'description',_text=parsed_word['jianjie'])
    sense.append(html.Element('br'))

    for desc in parsed_word['jieshi']:
        make_sub_elem(sense, 'description',_text=desc)
        sense.append(html.Element('br'))
    make_sub_elem(dict_root,'hr')
    return True







map_file_name=os.path.join(base_dir,'word_content_map-1-2-3')
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
#make_sub_elem(head,'link',{'href':'./KindleHandianSC.css','rel':"stylesheet", 'type':"text/css"})
css_text='''
.example_text {
    font-size:0.8rem;
    color: darkgray;
    font-family: STKai, "MKai PRC", Kai, "楷体";
}
'''
#make_sub_elem(head,'style',{'type':"text/css"},_text=css_text)
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
for word,content_map in word_conten_map.items():
    #对于一个文字
    #分析它的“基本解释”和“详细解释”,即页面上的标签ta
    #“基本解释”
    homo_no=1
    try:
        content_jiben=content_map['基本解释']
        if parse_print_tab_jiben(dict_root, homo_no, word,content_jiben):
            homo_no+=1
    except KeyError:
        pass
    #“详细解释”
    #try:
    #    content_xiangxi=content_map['详细解释']
    #    if parse_print_tab_xiangxi(dict_root, homo_no, word, content_xiangxi):
    #        homo_no+=1
    #except KeyError:
    #    pass
    #康熙字典
    #try:
    #    content_xiangxi=content_map['康熙字典']
    #    if parse_print_tab_kangxi(dict_root, homo_no, word, content_xiangxi):
    #        homo_no+=1
    #except KeyError:
    #    pass
    if homo_no>1:
        word_cnt+=1
print("一共有：",word_cnt,"个字。")
from FilterHtml import FilterHtml
filter_html= FilterHtml('font_images', _html_tree=html_root)
filter_html.run()
with open(os.path.join(out_dir,'KindleHanDianSCP.html'),'wb') as f:
    f.write(etree.tostring(filter_html.html_tree, encoding='utf-8', pretty_print=True, method='html'))
    f.close()

with open(os.path.join(out_dir,'manifest.txt'),'wb') as f:
    f.write(etree.tostring(filter_html.manifest, encoding='utf-8', pretty_print=True, method='html'))
    f.close()


#使用etree的tostring函数才可以输出<br/>这样的
#使用html.tostring只能输出<br>
#with open(os.path.join(out_dir,'KindleHanDianSC.html'),'wb') as f:
#    f.write(etree.tostring(html_root, encoding='utf-8', pretty_print=True, method='html'))
#    f.close()


