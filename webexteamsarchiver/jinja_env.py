import jinja2
from hurry.filesize import size, alternative


def datetime_format(date, format='%Y-%m-%dT%H:%M:%S'):
    return date.strftime(format)

def filesize_format(size_bytes):
    return size(int(size_bytes), system=alternative)

def person_letters(display_name):
    output = ""
    for name in display_name.upper().split():
        output += name[0]

    if len(output) > 2:
        return f"{output[0]}{output[-1]}"
    
    return output

env = jinja2.Environment(
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    loader=jinja2.PackageLoader('webexteamsarchiver', 'templates')
)

env.filters['datetime_format'] = datetime_format
env.filters['filesize_format'] = filesize_format
env.filters['person_letters'] = person_letters