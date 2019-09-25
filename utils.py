from abc import ABC, abstractmethod
from enum import Enum
# from xml.etree import ElementTree as et
from lxml import etree as et
from functools import partial


class QuestionType(Enum):
    Empty = 0
    SingleSelection = 1
    Judgement = 1 << 1


class Question(ABC):
    _type = ''

    def __init__(self, parent_element):
        self.caption_number = ''
        self.title = ''
        self.options = []
        self.answer = ''
        self.count = -1
        self.element = et.SubElement(parent_element, 'question')
        # self.bound_SubElement(a) === et.SubElement(self.element, a)
        self.bound_SubElement = partial(et.SubElement, self.element)



    def add_title(self, title: str):
        self.title += title

    def add_option(self, option: str):
        self.options.append(option)

    def add_anwser(self, answer):
        """暂存answer，会将旧有的answer加入title中"""
        self.title += self.answer
        self.answer = answer

    def has_title(self) -> bool:
        return True if self.title else False

    def has_answer(self):
        return True if self.answer else False

    def validate(self):
        if not (self.title and self.options and self.answer is not None):
            print(self.title)
            print(self.options)
            print(self.answer)
            raise Exception('有信息没有填写完成')

    def print_answer(self):
        print(self.title, self.answer)
    
    def get_meta_data(self):
        # 用于检查正确性
        return f"{self.title} [{self.answer}]\n"

    @abstractmethod
    def parse_answer(self):
        self.answer = self.answer.strip('\n').strip()[:-1].strip()


    def parse_options(self):
        self.options = (option.strip('\r').strip() for option in self.options)
        self.options = list(self.options)

    def parse_title(self):
        self.title = self.title.strip()

    @abstractmethod
    def export_XML(self):
        self.parse_answer()
        self.parse_options()
        self.parse_title()
        # self.print_answer()


        # <name>
        #   <text>这是一道判断题的名称</text>
        # </name>
        _n = self.bound_SubElement('name')
        _t = et.SubElement(_n, 'text')
        _t.text = f'{self.caption_number}{self._type}{self.count}'
        
        # <questiontext format="html">
        #     <text>{{ self.title }}</text>
        # </questiontext>
        _qt = self.bound_SubElement('questiontext')
        _qt.set('format', 'html')
        _t = et.SubElement(_qt, 'text')
        _t.text = et.CDATA(f'<p>{self.title}</p>')

        #  <generalfeedback format="html">
        #     <text></text>
        #  </generalfeedback>
        _fb = self.bound_SubElement('generalfeedback')
        _qt.set('format', "html")
        _t = et.SubElement(_fb, 'text')

        # <defaultgrade>1.0000000</defaultgrade>
        self.bound_SubElement('defaultgrade').text = '1.0000000'

        # <penalty>1.0000000</penalty>
        self.bound_SubElement('penalty').text = '1.0000000'

        # <hidden>0</hidden>
        self.bound_SubElement('hidden').text = '0'


class SingleSelection(Question):
    _type = "单项选择"

    def print_answer(self):
        print(self.title, f'[{self.options[self.answer]}]')

    def get_meta_data(self):
        # 用于检查正确性
        return f"{self.title} [{self.options[self.answer]}]\n"


    def parse_answer(self):
        super().parse_answer()
        if len(self.answer) != 1:
            raise Exception('选项答案只能用一个字符 ' + self.answer)
        self.answer = self.answer.lower()
        self.answer = ord(self.answer) - ord('a')

    def export_XML(self):
        super().export_XML()
        super().validate()

        # 判断选项是否存在
        if len(self.options) < self.answer:
            raise Exception('[缺少选项]请检查选项是否存在，或者是否放在不同行中\n'+self.title)

        # multichoice
        self.element.set('type', 'multichoice')

        # <single>true</single>
        self.bound_SubElement('single').text = 'true'
        # <shuffleanswers>true</shuffleanswers>
        self.bound_SubElement('shuffleanswers').text = 'true'
        # <answernumbering>abc</answernumbering>
        self.bound_SubElement('answernumbering').text = 'abc'

        # <answer fraction="0" format="html">
        #   <text>
        #       <![CDATA[ <p>选项2</p> ]]>
        #   </text>
        #   <feedback format="html">
        #       <text/>
        #   </feedback>
        # </answer>
        for idx, option in enumerate(self.options):
            ans = self.bound_SubElement('answer')
            ans_fraction = "100" if idx == self.answer else "0"
            ans.set('fraction', ans_fraction)
            ans.set('format', 'html')
            et.SubElement(ans, "text").text = et.CDATA(f"<p>{option}</p>")
            _fb = et.SubElement(ans, "feedback")
            _fb.set("format", "html")
            et.SubElement(_fb, "text")


class Judgement(Question):
    _type = "判断题"

    def parse_answer(self):
        super().parse_answer()
        self.answer = True if 'T' in self.answer or 't' in self.answer else False

    def export_XML(self):
        super().export_XML()
        self.element.set('type', 'truefalse')

        # <answer fraction="0" format="moodle_auto_format">
        # <text>true</text>
        # <feedback format="html">
        # <text/>
        # </feedback>
        # </answer>
        ans = self.bound_SubElement("answer")
        ans.set("fraction", "100" if self.answer else '0')
        ans.set("format", 'moodle_auto_format')
        et.SubElement(ans, "text").text = 'true'
        _fb = et.SubElement(ans, "feedback")
        _fb.set("format", "html")
        et.SubElement(_fb, "text")

        # <answer fraction="100" format="moodle_auto_format">
        # <text>false</text>
        # <feedback format="html">
        # <text/>
        # </feedback>
        # </answer>

        ans = self.bound_SubElement("answer")
        ans.set("fraction", "100" if not self.answer else '0')
        ans.set("format", 'moodle_auto_format')
        et.SubElement(ans, "text").text = 'false'
        _fb = et.SubElement(ans, "feedback")
        _fb.set("format", "html")
        et.SubElement(_fb, "text")


def question_factory(enum: QuestionType, parent_element):
    if enum == QuestionType.Judgement:
        return Judgement(parent_element)
    elif enum == QuestionType.SingleSelection:
        return SingleSelection(parent_element)
    else:
        raise Exception('[question_factory] not a valid enum.')
