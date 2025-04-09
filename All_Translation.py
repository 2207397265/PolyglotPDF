import time
import os
import Deepl_Translation as dt
import YouDao_translation as yt
import Bing_translation as bt
import LLMS_translation as lt
import asyncio
from functools import wraps

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

def retry_on_error(max_retries=2, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper_sync(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries <= max_retries:
                        print(f"Error occurred: {str(e)}")
                        print(f"Retrying... (Attempt {retries} of {max_retries})")
                        time.sleep(delay)
                    else:
                        print(f"Max retries reached. Skipping... Final error: {str(e)}")
                        return None
            return None

        async def wrapper_async(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries <= max_retries:
                        print(f"Error occurred: {str(e)}")
                        print(f"Retrying... (Attempt {retries} of {max_retries})")
                        await asyncio.sleep(delay)
                    else:
                        print(f"Max retries reached. Skipping... Final error: {str(e)}")
                        return None
            return None

        return wrapper_async if asyncio.iscoroutinefunction(func) else wrapper_sync
    return decorator

class Online_translation:
    def __init__(self, original_language, target_language, translation_type, texts_to_process=[]):
        self.model_name = f"opus-mt-{original_language}-{target_language}"
        self.original_text = texts_to_process
        self.target_language = target_language
        self.original_lang = original_language
        self.translation_type = translation_type

    def run_async(self, coro):
        return loop.run_until_complete(coro)

    def translation(self):
        print('翻译api', self.translation_type)
        if self.translation_type == 'deepl':
            translated_list = self.deepl_translation()
        elif self.translation_type == 'youdao':
            translated_list = self.youdao_translation()
        elif self.translation_type == 'bing':
            translated_list = self.bing_translation()
        elif self.translation_type == 'openai':
            translated_list = self.run_async(self.openai_translation())
        elif self.translation_type == 'deepseek':
            translated_list = self.run_async(self.deepseek_translation())
        elif self.translation_type == 'Doubao':
            translated_list = self.run_async(self.Doubao_translation())
        elif self.translation_type == 'Qwen':
            translated_list = self.run_async(self.Qwen_translation())
        elif self.translation_type == 'Grok':
            translated_list = self.run_async(self.Grok_translation())
        elif self.translation_type == 'ThirdParty':
            translated_list = self.run_async(self.ThirdParty_translation())
        elif self.translation_type == 'GLM':
            translated_list = self.run_async(self.GLM_translation())
        else:
            translated_list = self.deepl_translation()

        return translated_list

    @retry_on_error()
    def deepl_translation(self):
        translated_texts = dt.translate(
            texts=self.original_text,
            original_lang=self.original_lang,
            target_lang=self.target_language
        )
        return translated_texts

    @retry_on_error()
    def youdao_translation(self):
        translated_texts = yt.translate(
            texts=self.original_text,
            original_lang=self.original_lang,
            target_lang=self.target_language
        )
        return translated_texts

    @retry_on_error()
    def bing_translation(self):
        try:
            translated_texts = bt.translate(
                texts=self.original_text,
                original_lang=self.original_lang,
                target_lang=self.target_language
            )
            print(f"Bing translation completed: {len(translated_texts)} texts processed")
            return translated_texts
        except Exception as e:
            print(f"Error in Bing translation: {e}")
            return [""] * len(self.original_text)

    @retry_on_error()
    async def openai_translation(self):
        translator = lt.Openai_translation()
        translated_texts = await translator.translate(
            texts=self.original_text,
            original_lang=self.original_lang,
            target_lang=self.target_language
        )
        return translated_texts

    @retry_on_error()
    async def deepseek_translation(self):
        translator = lt.Deepseek_translation()
        translated_texts = await translator.translate(
            texts=self.original_text,
            original_lang=self.original_lang,
            target_lang=self.target_language
        )
        return translated_texts

    @retry_on_error()
    async def Doubao_translation(self):
        translator = lt.Doubao_translation()
        translated_texts = await translator.translate(
            texts=self.original_text,
            original_lang=self.original_lang,
            target_lang=self.target_language
        )
        return translated_texts

    @retry_on_error()
    async def Qwen_translation(self):
        translator = lt.Qwen_translation()
        translated_texts = await translator.translate(
            texts=self.original_text,
            original_lang=self.original_lang,
            target_lang=self.target_language
        )
        return translated_texts

    @retry_on_error()
    async def Grok_translation(self):
        translator = lt.Grok_translation()
        try:
            translated_texts = await translator.translate(
                texts=self.original_text,
                original_lang=self.original_lang,
                target_lang=self.target_language
            )
            print(f"Grok translation completed: {len(translated_texts)} texts processed")
            return translated_texts
        except Exception as e:
            print(f"Error in Grok translation: {e}")
            return [""] * len(self.original_text)

    @retry_on_error()
    async def ThirdParty_translation(self):
        translator = lt.ThirdParty_translation()
        try:
            translated_texts = await translator.translate(
                texts=self.original_text,
                original_lang=self.original_lang,
                target_lang=self.target_language
            )
            print(f"ThirdParty translation completed: {len(translated_texts)} texts processed")
            return translated_texts
        except Exception as e:
            print(f"Error in ThirdParty translation: {e}")
            return [""] * len(self.original_text)

    @retry_on_error()
    async def GLM_translation(self):
        translator = lt.GLM_translation()
        try:
            translated_texts = await translator.translate(
                texts=self.original_text,
                original_lang=self.original_lang,
                target_lang=self.target_language
            )
            print(f"GLM translation completed: {len(translated_texts)} texts processed")
            return translated_texts
        except Exception as e:
            print(f"Error in GLM translation: {e}")
            return [""] * len(self.original_text)

    

t = time.time()
def split_text_to_fit_token_limit(text, encoder, index_text, max_length=280):
    tokens = encoder.encode(text)
    if len(tokens) <= max_length:
        return [(text, len(tokens), index_text)]

    split_points = [i for i, token in enumerate(tokens) if encoder.decode([token]).strip() in [' ', '.', '?', '!','！','？','。']]
    parts = []
    last_split = 0
    for i, point in enumerate(split_points + [len(tokens)]):
        if point - last_split > max_length:
            part_tokens = tokens[last_split:split_points[i - 1]]
            parts.append((encoder.decode(part_tokens), len(part_tokens), index_text))
            last_split = split_points[i - 1]
        elif i == len(split_points):
            part_tokens = tokens[last_split:]
            parts.append((encoder.decode(part_tokens), len(part_tokens), index_text))

    return parts

def process_texts(texts, encoder):
    processed_texts = []
    for i, text in enumerate(texts):
        sub_texts = split_text_to_fit_token_limit(text, encoder, i)
        processed_texts.extend(sub_texts)
    return processed_texts

def calculate_split_points(processed_texts, max_tokens=425):
    split_points = []
    current_tokens = 0

    for i in range(len(processed_texts) - 1):
        current_tokens = processed_texts[i][1]
        next_tokens = processed_texts[i + 1][1]

        if current_tokens + next_tokens > max_tokens:
            split_points.append(i)

    split_points.append(len(processed_texts) - 1)

    return split_points

def translate(texts,original_language,target_language):
    from transformers import pipeline, AutoTokenizer

    model_name = f"./opus-mt-{original_language}-{target_language}"
    pipe = pipeline("translation", model=model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    result = pipe(texts)

    result_values = [d['translation_text'] for d in result]

    return result_values

def batch_translate(processed_texts, split_points,original_language,target_language):
    translated_texts = []
    index_mapping = {}

    start_index = 0

    for split_point in split_points:
        batch = processed_texts[start_index:split_point + 1]
        batch_texts = [text for text, _, _ in batch]
        translated_batch = translate(texts=batch_texts,original_language=original_language,target_language=target_language)

        for translated_text, (_, _, int_value) in zip(translated_batch, batch):
            if int_value in index_mapping:
                translated_texts[index_mapping[int_value]] += " " + translated_text
            else:
                index_mapping[int_value] = len(translated_texts)
                translated_texts.append(translated_text)

        start_index = split_point + 1

    return translated_texts

