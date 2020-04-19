"""Jinja Configuration.

Copyright (c) 2018-2020 Cisco and/or its affiliates.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import jinja2
import datetime
import re
from hurry.filesize import size, alternative

__all__ = ['env', 'sanitize_name']


def filesize_format(size_bytes):
    if not str(size_bytes).isdigit():
        return 0

    return size(int(size_bytes), system=alternative)


def person_letters(display_name: str) -> str:
    if not display_name:
        return "Person Not Found"

    output = ""
    for name in display_name.upper().split():
        output += name[0]

    if len(output) > 2:
        return f"{output[0]}{output[-1]}"

    return output


def datetime_format(date: datetime, format: str) -> str:
    if not date:
        return str(date)

    return date.strftime(format)


def sanitize_name(text: str) -> str:
    text = str(text).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', text)


def format_msg(text: str, thread: bool) -> str:
    spaces = " " * 2
    if thread:
        spaces *= 3

    if isinstance(text, str) and "\n" in text:
        text = re.sub("\\n", f"\\n{spaces}", text)
        text = f"{spaces}{text}"
        return f"\n{text}"

    return text


env = jinja2.Environment(
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    loader=jinja2.PackageLoader('webexteamsarchiver', 'templates')
)

env.filters['filesize_format'] = filesize_format
env.filters['person_letters'] = person_letters
env.filters['datetime_format'] = datetime_format
env.filters['sanitize_name'] = sanitize_name
env.filters['format_msg'] = format_msg
