import math
import All_Translation as at
from PIL import Image
import pytesseract
import time
import fitz
import os
import unicodedata
import download_model
import load_config
import re
from datetime import datetime
import pdf_thumbnail

config = load_config.load_config()
translation_type = config['default_services']['Translation_api']
translation = config['default_services']['Enable_translation']
use_mupdf = not config['default_services']['ocr_model']

PPC = config['PPC']
print('ppc',PPC)
line_model = config['default_services']['line_model']
print('line',line_model)
# print(use_mupdf,'mupdf值')
# print('当前',config['count'])



def get_font_by_language(target_language):
    font_mapping = {
        'zh': "'Microsoft YaHei', 'SimSun'",  # 中文
        'en': "'Times New Roman', Arial",      # 英文
        'ja': "'MS Mincho', 'Yu Mincho'",     # 日文
        'ko': "'Malgun Gothic'",              # 韩文
    }
    # 如果找不到对应语言，返回默认字体
    return font_mapping.get(target_language, "'Times New Roman', Arial")


def is_math(text, page_num,font_info):
    """
    判断文本是否为非文本（如数学公式或者长度小于4的文本）
    """


    # 判断文本长度
    text_len = len(text)
    if text_len < 4:
        return True
    math_fonts = [
        # Computer Modern Math
        'CMMI', 'CMSY', 'CMEX',
        'CMMI5', 'CMMI6', 'CMMI7', 'CMMI8', 'CMMI9', 'CMMI10',
        'CMSY5', 'CMSY6', 'CMSY7', 'CMSY8', 'CMSY9', 'CMSY10',

        # AMS Math
        'MSAM', 'MSBM', 'EUFM', 'EUSM',

        # Times/Palatino Math
        'TXMI', 'TXSY', 'PXMI', 'PXSY',

        # Modern Math
        'CambriaMath', 'AsanaMath', 'STIXMath', 'XitsMath',
        'Latin Modern Math', 'Neo Euler'
    ]
    # 检查文本长度是否小于50且字体是否在数学字体列表中
    if text_len < 70 and any(math_font in font_info for math_font in math_fonts):
        return True

    if 15 < text_len <100:
        # 使用正则表达式找出所有5个或更多任意字符连续组成的单词
        long_words = re.findall(r'\S{5,}', text)
        if len(long_words) < 2:
            return True


    # 分行处理
    lines = text.split('\n')
    len_lines = len([line for line in lines if line.strip()])

    # 找到长度最小和最大的行
    min_line_len = min((len(line) for line in lines if line.strip()), default=text_len)
    max_line_len = max((len(line) for line in lines), default=text_len)

    # 计算空格比例
    newline_count = text.count('\n')
    total_spaces = text.count(' ') + (newline_count * 5)
    space_ratio = total_spaces / text_len if text_len > 0 else 0

    # 定义数学符号集合
    math_symbols = "=∑θ∫∂√±ΣΠfδλσε∋∈µ→()|−ˆ,.+*/[]{}^_<>~#%&@!?;:'\"\\-"

    # 检查是否存在完整单词(5个或更多非数学符号的连续字符)
    text_no_spaces = text.replace(" ", "")

    # 创建一个正则表达式，匹配5个或更多连续的非数学符号字符
    pattern = r'[^' + re.escape(math_symbols) + r']{5,}'
    has_complete_word = bool(re.search(pattern, text_no_spaces))

    # 如果没有完整单词，认为是非文本
    if not has_complete_word:
        return True


    # 计算数字占比
    digit_count = sum(c.isdigit() for c in text)
    digit_ratio = digit_count / text_len if text_len > 0 else 0

    # 如果数字占比超过30%，返回True
    if digit_ratio > 0.3:
        return True





    # 检查数学公式
    math_symbols = set("=∑θ∫∂√±ΣΠfδλσε∋∈µ→()|−ˆ,...")
    # 数学公式判断条件2:包含至少2个数学符号且总文本较短
    if sum(1 for sym in math_symbols if sym in text) >= 2 and len(text_no_spaces) < 25:
        return True

    # 数学公式判断条件1:包含至少2个数学符号且行短且行数少且最大行长度小
    if sum(1 for sym in math_symbols if sym in text) >= 2 and min_line_len < 10 and len_lines < 5 and max_line_len < 35:

        return True

    # 数学公式判断条件3:包含至少2个数学符号且空格比例高
    if sum(1 for sym in math_symbols if sym in text) >= 2 and space_ratio > 0.5:

        return True

    return False

def line_non_text(text):
    """
    判断文本是否由纯数字和所有(Unicode)标点符号组成
    参数：
        text: 待检查的文本
    返回：
        bool: 如果文本由纯数字和标点符号组成返回True，否则返回False
    """
    text = text.strip()
    if not text:
        return False
    for ch in text:
        # 使用 unicodedata.category() 获取字符在 Unicode 标准中的分类
        # 'Nd' 代表十进制数字 (Number, Decimal digit)
        # 'P' 代表各种标点 (Punctuation)，如 Po, Ps, Pe, 等
        cat = unicodedata.category(ch)
        if not (cat == 'Nd' or cat.startswith('P')):
            return False
    return True


def is_non_text(text):
    """
    判断是否为参考文献格式
    参数：
    text: 待检查的文本
    返回：
    bool: 如果是参考文献格式返回True，否则返回False
    """
    # 去除开头的空白字符
    text = text.lstrip()

    # 检查是否以[数字]开头
    pattern = r'^\[\d+\]'

    if re.match(pattern, text):
        return True

    return False
font_collection = []


class main_function:
    def __init__(self, pdf_path,
                 original_language, target_language,
                 DPI=72,):
        """
        这里的参数与原来保持一致或自定义。主要多加一个 self.pages_data 用于存储所有页面的提取结果。
        """

        self.pdf_path = pdf_path
        self.pdf_path = pdf_path
        self.full_path ='./static/original/' + pdf_path
        self.doc = fitz.open(self.full_path)

        self.original_language = original_language
        self.target_language = target_language
        self.DPI = DPI
        self.translation = translation
        self.translation_type = translation_type
        self.use_mupdf = use_mupdf
        self.line_model = line_model

        self.t = time.time()
        # 新增一个全局列表，用于存所有页面的 [文本, bbox]，以及翻译后结果
        # 形式: self.pages_data[page_index] = [ [原文, bbox], [原文, bbox], ... ]
        self.pages_data = []

    def main(self):
        """
        主流程函数。只做“计数更新、生成缩略图、建条目”等老逻辑，替换原来在这里的逐页翻译写入。
        但是保留 if use_mupdf: for... self.start(...) else: for... self.start(...)
        不做“翻译和写入”的动作，而是只做“提取文本”。
        提取完所有页面后，批量翻译，再统一写入 PDF。
        """
        # 1. 计数和配置信息
        load_config.update_count()
        config = load_config.load_config()
        count = config["count"]


        # 2. 生成 PDF 缩略图 (保留原逻辑)
        pdf_thumbnail.create_pdf_thumbnail(self.full_path, width=400)

        # 3. 创建新条目（保留原逻辑）
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_entry = {
            "index": count,
            "date": current_time,
            "name": self.pdf_path,
            "original_language": self.original_language,
            "target_language": self.target_language,
            "read": "0",
            "statue": "0"
        }
        load_config.add_new_entry(new_entry)

        # 4. 保留原先判断是否 use_mupdf 的代码，以便先提取文本
        if self.use_mupdf:
            # 使用 PyMuPDF 直接获取文本块 (不要改动这段判断逻辑)
            for i in range(self.doc.page_count):
                self.start(image=None, pag_num=i)   # 只做提取，不做翻译写入
        else:
            # OCR 模式
            zoom = self.DPI / 72
            mat = fitz.Matrix(zoom, zoom)
            for i, page in enumerate(self.doc):
                pix = page.get_pixmap(matrix=mat)
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                # 如果需要保存图像到文件，可自行保留或注释
                # image.save(f'page_{i}.jpg', 'JPEG')
                self.start(image=image, pag_num=i)  # 只做提取，不做翻译写入

        # 5. 若开启翻译，则批量翻译所有提取的文本

        self.batch_translate_pages_data(
                original_language=self.original_language,
                target_language=self.target_language,
                translation_type=self.translation_type,
                batch_size=PPC
            )

        # 6. 将翻译结果统一写入 PDF（覆盖+插入译文）
        self.apply_translations_to_pdf()

        # 7. 保存 PDF、更新状态
        pdf_name, _ = os.path.splitext(self.pdf_path)
        self.doc.ez_save(
            f"./static/target/{pdf_name}_{self.target_language}.pdf",
            garbage=4,
            deflate=True
        )
        load_config.update_file_status(count, statue="1")  # statue = "1"

        # 8. 打印耗时
        end_time = time.time()
        print(end_time - self.t)

    def start(self, image, pag_num):
        """
        原先逐页处理的函数，现仅负责“提取文本并存储在 self.pages_data[pag_num]”。
        不在这里直接翻译或写回 PDF。
        """
        # 确保 self.pages_data 有 pag_num 对应的列表
        while len(self.pages_data) <= pag_num:
            self.pages_data.append([])  # 每个元素是 [ [text, (x0,y0,x1,y1)], ... ]

        page = self.doc.load_page(pag_num)

        if self.line_model and self.use_mupdf:
            def snap_angle_func(angle):
                """
                将任意角度自动映射到 0、90、180、270 四个值之一。
                """
                # 将角度映射到 [0, 360) 区间
                angle = abs(angle) % 360
                # 选取最接近的标准角度
                possible_angles = [0, 90, 180, 270]
                return min(possible_angles, key=lambda x: abs(x - angle))

            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block.get("type") == 0:  # 文本块
                    font_info = None
                    # 遍历每一行
                    for line in block["lines"]:
                        # 1) 拼接文本（减少反复 += 操作）
                        span_texts = [span["text"] for span in line["spans"] if "text" in span]
                        line_text = "".join(span_texts).strip()

                        # 2) 如果行文本为空或仅含数字标点，就跳过
                        if not line_text or line_non_text(line_text):
                            continue

                        # 3) 此时才计算旋转角度，避免空行浪费
                        direction = line.get("dir", [1.0, 0.0])
                        raw_angle = math.degrees(math.atan2(direction[1], direction[0]))
                        angle = snap_angle_func(raw_angle)

                        # 4) 只在需要时提取字体信息
                        if not font_info:
                            for span in line["spans"]:
                                if "font" in span:
                                    font_info = span["font"]
                                    break
                        if font_info and font_info not in font_collection:
                            font_collection.append(font_info)

                        line_bbox = line.get("bbox")
                        # 5) 加入提取结果
                        self.pages_data[pag_num].append([
                            line_text,  # 原文
                            tuple(line_bbox),  # BBox
                            None,  # 预留翻译文本
                            angle  # 行角度
                        ])


        # 如果用 PyMuPDF 提取文字
        elif self.use_mupdf and image is None:
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block.get("type") == 0:  # 文本块
                    bbox = block["bbox"]
                    text = ""
                    font_info = None
                    for line in block["lines"]:
                        for span in line["spans"]:
                            span_text = span["text"].strip()
                            if span_text:
                                text += span_text + " "
                                if not font_info and "font" in span:
                                    font_info = span["font"]
                    text = text.strip()
                    if text and not is_math(text, pag_num, font_info) and not is_non_text(text):
                        self.pages_data[pag_num].append([text, tuple(bbox),None])

        else:
            # OCR 提取文字
            config = load_config.load_config()
            tesseract_path = config['ocr_services']['tesseract']['path']
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

            Full_width, Full_height = image.size
            ocr_result = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

            current_paragraph_text = ''
            paragraph_bbox = {
                'left': float('inf'),
                'top': float('inf'),
                'right': 0,
                'bottom': 0
            }
            current_block_num = None
            Threshold_width = 0.06 * Full_width
            Threshold_height = 0.006 * Full_height

            for i in range(len(ocr_result['text'])):
                block_num = ocr_result['block_num'][i]
                text_ocr = ocr_result['text'][i].strip()
                left = ocr_result['left'][i]
                top = ocr_result['top'][i]
                width = ocr_result['width'][i]
                height = ocr_result['height'][i]

                if text_ocr and not is_math(text_ocr, pag_num, font_info='22') and not is_non_text(text_ocr):

                    # 若换 block 或段落间隔较大，则保存上一段
                    if (block_num != current_block_num or
                       (abs(left - paragraph_bbox['right']) > Threshold_width and
                        abs(height - (paragraph_bbox['bottom'] - paragraph_bbox['top'])) > Threshold_height and
                        abs(left - paragraph_bbox['left']) > Threshold_width)):

                        if current_paragraph_text:
                            # 转换到 PDF 坐标
                            Full_rect = page.rect
                            w_points = Full_rect.width
                            h_points = Full_rect.height

                            x0_ratio = paragraph_bbox['left'] / Full_width
                            y0_ratio = paragraph_bbox['top'] / Full_height
                            x1_ratio = paragraph_bbox['right'] / Full_width
                            y1_ratio = paragraph_bbox['bottom'] / Full_height

                            x0_pdf = x0_ratio * w_points
                            y0_pdf = y0_ratio * h_points
                            x1_pdf = x1_ratio * w_points
                            y1_pdf = y1_ratio * h_points

                            self.pages_data[pag_num].append([
                                current_paragraph_text.strip(),
                                (x0_pdf, y0_pdf, x1_pdf, y1_pdf)
                            ])

                        # 重置
                        current_paragraph_text = ''
                        paragraph_bbox = {
                            'left': float('inf'),
                            'top': float('inf'),
                            'right': 0,
                            'bottom': 0
                        }
                        current_block_num = block_num

                    # 继续累加文本
                    current_paragraph_text += text_ocr + " "
                    paragraph_bbox['left'] = min(paragraph_bbox['left'], left)
                    paragraph_bbox['top'] = min(paragraph_bbox['top'], top)
                    paragraph_bbox['right'] = max(paragraph_bbox['right'], left + width)
                    paragraph_bbox['bottom'] = max(paragraph_bbox['bottom'], top + height)

            # 收尾：最后一段存入
            if current_paragraph_text:
                Full_rect = page.rect
                w_points = Full_rect.width
                h_points = Full_rect.height

                x0_ratio = paragraph_bbox['left'] / Full_width
                y0_ratio = paragraph_bbox['top'] / Full_height
                x1_ratio = paragraph_bbox['right'] / Full_width
                y1_ratio = paragraph_bbox['bottom'] / Full_height

                x0_pdf = x0_ratio * w_points
                y0_pdf = y0_ratio * h_points
                x1_pdf = x1_ratio * w_points
                y1_pdf = y1_ratio * h_points

                self.pages_data[pag_num].append([
                    current_paragraph_text.strip(),
                    (x0_pdf, y0_pdf, x1_pdf, y1_pdf),
                    None
                ])

        # 注意：这里不做翻译、不插入 PDF，只负责“收集文本”到 self.pages_data

    def batch_translate_pages_data(self, original_language, target_language,
                                   translation_type, batch_size=PPC ):
        """PPC (Pages Per Call)
        分批翻译 pages_data，每次处理最多 batch_size 页的文本，避免一次性过多。
        将译文存回 self.pages_data 的第三个元素，如 [原文, bbox, 译文]
        """
        total_pages = len(self.pages_data)
        start_idx = 0

        while start_idx < total_pages:
            end_idx = min(start_idx + batch_size, total_pages)

            # 收集该批次的所有文本
            batch_texts = []
            for i in range(start_idx, end_idx):
                for block in self.pages_data[i]:
                    batch_texts.append(block[0])  # block[0] = 原文

            # 翻译


            if self.translation and use_mupdf:
                translation_list = at.Online_translation(
                    original_language=original_language,
                    target_language=target_language,
                    translation_type=translation_type,
                    texts_to_process=batch_texts
                ).translation()
            elif self.translation and not use_mupdf:
                # 离线翻译
                translation_list = at.Offline_translation(
                    original_language=original_language,
                    target_language=target_language,
                    texts_to_process=batch_texts
                ).translation()
            else:

                translation_list = batch_texts



            # 回填译文
            idx_t = 0
            for i in range(start_idx, end_idx):
                for block in self.pages_data[i]:
                    # 在第三个位置添加翻译文本
                    block[2] = translation_list[idx_t]
                    idx_t += 1

            start_idx += batch_size

    def apply_translations_to_pdf(self):
        """
        统一对 PDF 做“打码/打白 + 插入译文”操作
        """
        for page_index, blocks in enumerate(self.pages_data):
            page = self.doc.load_page(page_index)

            for block in blocks:
                original_text = block[0]
                coords = block[1]  # (x0, y0, x1, y1)
                # 如果第三个元素是译文，则用之，否则用原文
                translated_text = block[2] if len(block) >= 3 else original_text

                if self.line_model:
                    angle = block[3] if len(block) > 3 else 0

                else:
                    angle = 0

                rect = fitz.Rect(*coords)

                # 先尝试使用 Redact 遮盖
                try:
                    page.add_redact_annot(rect)
                    page.apply_redactions()
                except Exception as e:
                    # 若 Redact 失败，改用白色方块覆盖
                    annots = list(page.annots() or [])
                    if annots:
                        page.delete_annot(annots[-1])
                    try:
                        page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                    except Exception as e2:
                        print(f"创建白色画布时发生错误: {e2}")
                    print(f"应用重编辑时发生错误: {e}")



                page.insert_htmlbox(
                    rect,
                    translated_text,
                    css="""
                * {
                    font-family: "Microsoft YaHei";
                    /* 这行可把内容改成粗体, 可写 "bold" 或数字 (100–900) */
                    font-weight: 100;
                    /* 这里可以使用标准 CSS 颜色写法, 例如 #FF0000、rgb() 等 */
                    color:  #333333;
                }
                """,
                    rotate=angle

                )


        # 完成后不会立即保存，需要在 main(...) 里 self.doc.ez_save(...)

if __name__ == '__main__':

    main_function(original_language='auto', target_language='zh', pdf_path='demo.pdf').main()
