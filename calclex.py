#! python
import os
import sys
from pathlib import Path
import chardet
import ply.lex as lex
# from xml.etree import ElementTree as et
from lxml import etree as et
from ply.lex import TOKEN
from pathlib import Path
import utils

path = '.'
if len(sys.argv) > 1:
    path = sys.argv[1]


def my_parser(filename: str):

    # list of states
    states = (
        ('category', 'inclusive'),
        ('title', 'inclusive'),
        ('titlebracket', 'inclusive'),
        ('titlebrackethalf', 'inclusive'),
        ('options', 'inclusive')
    )

    # List of token names.   This is always required
    tokens = (
        'HAN',
        'NUMBER',
        'DOT',
        'PLUS',
        'MINUS',
        'TIMES',
        'DIVIDE',
        'LPAREN',
        'RPAREN',
        'CATEGORY',
        'CATEGORYNUMBER',
        'TITLE',
        'TITLECOMMENT',
        'OPTION',
        'OPTIONNUMBER',
        'ANSWER',
        'ANSWERWITHNEWLINE',
        'REPO',
    )

    # GLOBAL VERIABLES
    # same as category
    status = utils.QuestionType.Empty
    adaptor = None
    data = et.Element('quiz')
    caption_number = ''
    count = 1
    repo_name = ''
    meta_data = ''  # 记录标题和答案，用于核对信息

    _q = et.SubElement(data, 'question')
    _q.set('type', 'category')
    _c = et.SubElement(_q, 'category')
    _t = et.SubElement(_c, 'text')
    _t.text = '$course$/' + Path(filename).name

    space = r'\s'
    spaces = r'\s?'
    han = r'[\u4e00-\u9fff]'
    han_mark = r'，。？：'
    han_brace = r'（）【】'
    hans = han+r'+'

    category_digit = r'[一二三四五六七八九十]'
    category_number = r'(' + category_digit + r'+)'

    # t_CATEGORY = category_number + r'、' + spaces + r'.*'

    @TOKEN(category_number + r'、')
    def t_INITIAL_CATEGORYNUMBER(t):
        nonlocal caption_number
        # 记录标题信息
        caption_number = t.value
        count = 1

        t.lexer.begin('category')

    @TOKEN('.+')
    def t_INITIAL_REPO(t):
        nonlocal repo_name, _t
        repo_name += t.value
        _t.text = repo_name

    @TOKEN(r'[A-Z][．\.]?')
    def t_category_OPTIONNUMBER(t):
        t.lexer.begin('options')

    @TOKEN(r'[(（]')
    def t_title_TITLECOMMENT(t):
        nonlocal adaptor

        t.lexer.begin('titlebracket')

    # title 的编号
    @TOKEN(r'\d+[．\.]')
    def t_category_TITLE(t):
        nonlocal status, adaptor, data, caption_number, count, meta_data
        if adaptor:
            adaptor.export_XML()
            meta_data += adaptor.get_meta_data()

        adaptor = utils.question_factory(status, data)
        adaptor.caption_number = caption_number
        adaptor.count = count
        count += 1

        t.lexer.begin('title')

    @TOKEN(r'.+')
    def t_category_CATEGORY(t):
        nonlocal status, adaptor
        if '单' in t.value or '选择' in t.value:
            # 单项选择题
            status = utils.QuestionType.SingleSelection
        elif '判断' in t.value:
            # 判断题
            status = utils.QuestionType.Judgement
        else:
            if t.value[0].isupper():
                raise Exception(
                    f'[第{t.lineno}行][CATEGORY]无法决定类型\n{t.value}\n [请检查标点符号]')
            raise Exception(
                f'[第{t.lineno}行][CATEGORY]无法决定类型 [{t.value.encode()}][{t.value}]')
        # print(status)
        return t

    @TOKEN(r'.+')
    def t_options_OPTION(t):
        # !IMPORTANT 不能换行，换行即认为选项结束
        nonlocal status, adaptor

        if status == utils.QuestionType.SingleSelection:
            # 单选的选项
            adaptor.add_option(t.value)
        elif status == utils.QuestionType.Empty:
            raise Exception("在类别之前遇到了选项")
        else:
            # 判断题不应该有选项
            raise Exception('status Error')
        t.lexer.begin('category')
        return t

    # @TOKEN(r'.\s*）\s*\n')
    # def t_titlebracket_ANSWERWITHNEWLINE(t):
    #     # 必须首先有题干
    #     nonlocal status, adaptor

    #     if status == utils.QuestionType.SingleSelection:
    #         # 转换成具体的索引 int A/a -> 0, B/b -> 1, ...
    #         adaptor.add_anwser(t.value)
    #     elif status == utils.QuestionType.Judgement:
    #         # 转换成具体的正确与否 bool
    #         adaptor.add_anwser(t.value)
    #     elif status == utils.QuestionType.Empty:
    #         raise Exception("在类别之前遇到了答案")
    #     else:
    #         raise Exception('status Error')
    #     t.lexer.begin('category')
    #     return t

    # TODO 增加半角支持，禁止嵌套
    @TOKEN(r'[A-Z]\s*[）)]')
    def t_titlebracket_ANSWER(t):
        # 必须首先有题干, 使用大写英文字母表示选项
        nonlocal status, adaptor

        if status == utils.QuestionType.SingleSelection:
            # 转换成具体的索引 int A/a -> 0, B/b -> 1, ...
            adaptor.add_anwser(t.value)
            # 只有单选题才加入占位的括号
            adaptor.add_title('（ ）')
        elif status == utils.QuestionType.Judgement:
            # 转换成具体的正确与否 bool
            adaptor.add_anwser(t.value)
        elif status == utils.QuestionType.Empty:
            raise Exception("在类别之前遇到了答案")
        else:
            raise Exception('status Error')
        t.lexer.begin('title')

        return t

    # TODO 增加半角支持
    @TOKEN(r'.*?[）)]')
    def t_titlebracket_TITLECOMMENT(t):
        nonlocal status, adaptor, data
        # print('[title]', t.value)
        text = '（' + t.value
        adaptor.add_title(text)
        t.lexer.begin('title')
        return t

    # title 的实际内容
    @TOKEN(r'[^(（\n]+')
    def t_title_TITLE(t):
        nonlocal status, adaptor, data
        # print('[title]', t.value)
        text = t.value
        adaptor.add_title(text)
        return t

    # print(t_CATEGORY)

    # + spaces + r'['+han + space + r']'
    # t_HAN = r'[\u4e00-\u9fff]+'
    t_DOT = r'\.、'

    # Regular expression rules for simple tokens
    t_PLUS = r'\+'
    t_MINUS = r'-'
    t_TIMES = r'\*'
    t_DIVIDE = r'/'
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    # A regular expression rule with some action code

    # def t_NUMBER(t):
    #     r'\d+'
    #     t.value = int(t.value)
    #     return t

    # Define a rule so we can track line numbers

    def t_title_newline(t):
        r'\n'
        nonlocal adaptor
        if adaptor.has_answer():
            # 这样可以在 title 中换行了
            t.lexer.begin('category')
        t.lexer.lineno += len(t.value)

    def t_ANY_newline(t):
        r'\n+'
        # print("hit newline")
        t.lexer.lineno += len(t.value)

    # A string containing ignored characters (spaces and tabs)
    t_ignore = ' \t　\r'

    def t_ANY_eof(t):
        nonlocal status, adaptor, meta_data
        if status and adaptor:
            adaptor.export_XML()
            meta_data += adaptor.get_meta_data()
        # print('eof')

    # Error handling rule
    def t_error(t):
        if t.value[0] == '':
            print('empty')
        # print(t.value[0].encode())
        # \xef\xbb\xbf is utf-8 with BOM
        print(f"[{t.lineno}] Illegal character '{t.value[0]}' {t.value[0].encode()}")
        t.lexer.skip(1)

    # Build the lexer
    lexer = lex.lex()

    def get_text() -> str:
        btxt = ""
        with open(f"{filename}.txt", 'rb') as f:
            btxt = f.read()
        btype = chardet.detect(btxt)
        # print(btype)
        if btype['encoding'] != 'utf-8':
            # convert to utf-8 and read.
            with open(f"{filename}.txt", 'wb') as f:
                f.write(btxt.decode(btype['encoding']).encode('utf-8'))
            with open(f"{filename}.txt", 'rb') as f:
                btxt = f.read()
        text = btxt.decode('utf-8')
        # print(text)

        # if text.encode().startswith(b'\xef\xbb\xbf'):
        #     # print(f'{filename} is utf-8 with BOM')
        #     with open(f"{filename}.txt", encoding='utf-8-sig') as f:
        #         txt = f.readlines()
        #     text = ''.join(txt)
        # print(text[0:2].encode())

        return text

    _data = get_text()
    # print(type(data), data)
    # Give the lexer some input
    lexer.input(_data)

    # Tokenize
    while True:
        tok = lexer.token()
        if not tok:
            break      # No more input
        # print(tok)

    # et.dump(data)
    return et.ElementTree(data), meta_data


p = Path(path)

META_DATA_FILENAME = p / '核对信息'
EXPORT_FILENEME = p / '导出数据'


if not Path(META_DATA_FILENAME).exists():
    os.mkdir(META_DATA_FILENAME)
if not Path(EXPORT_FILENEME).exists():
    os.mkdir(EXPORT_FILENEME)


for f in p.iterdir():

    if f.suffix == '.txt':
        try:
            tree, meta_data = my_parser(f'{ p / f.stem}')
            tree.write(f'{Path(EXPORT_FILENEME) / f.stem}-output.xml', encoding='UTF-8', xml_declaration=True,
                       pretty_print=True, strip_text=False)
            with open(f'{Path(META_DATA_FILENAME) / f.stem}-meta.txt', 'w', encoding="utf-8") as file:
                file.write(meta_data)
            print(f'{f} - 完成')
        except Exception as e:
            print(f'{f.name} - {e}')

print("转换完成，可以退出程序")

input()
input()