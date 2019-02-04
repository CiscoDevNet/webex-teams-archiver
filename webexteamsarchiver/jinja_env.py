"""Jinja Configuration.

Copyright (c) 2018-2019 Cisco and/or its affiliates.

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
    return size(int(size_bytes), system=alternative)


def person_letters(display_name: str) -> str:
    output = ""
    for name in display_name.upper().split():
        output += name[0]

    if len(output) > 2:
        return f"{output[0]}{output[-1]}"

    return output


def datetime_format(date: datetime, format: str) -> str:
    return date.strftime(format)


def sanitize_name(email: str) -> str:
    return re.sub('[^A-Za-z0-9]+', '_', email)


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