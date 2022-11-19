import re
import json

INPUT_FILENAME = "data/quicksave #119.sfs"
OUTPUT_FILENAME = "data/new.json"
PROPERTY = r"\s*\w+\s=\s*\w*\s*"
OBJECT = r"\s*[A-Za-z0-9]+\s*"
CAREER_LOG = "CAREER_LOG"


def do_parse_save_file(file, current, depth=0):
    while True:
        text = file.readline()

        if not text:
            return

        text = text.strip()

        if text == '}':
            return
        elif re.search(PROPERTY, text):
            name, value = [x.strip() for x in text.split('=', 1)]

            set_prop(current, name, value)
        elif re.search(OBJECT, text):
            child = {}
            set_prop(current, text, child)
            do_parse_save_file(file, child, depth + 1)


def set_prop(current, name, value):
    if name in current:
        if isinstance(current[name], list):
            current[name].append(value)
        else:
            current[name] = [current[name], value]
    else:
        current[name] = value


def parse_save_file(filename):
    f = open(filename, encoding='utf-8')
    root = {}
    try:
        do_parse_save_file(f, root)
    finally:
        f.close()
    return root


if __name__ == "__main__":

    save = parse_save_file(INPUT_FILENAME)

    with open(OUTPUT_FILENAME, mode='w') as f:
        f.write(json.dumps(save, indent=4))

    print(f"Done!  Results saved to {OUTPUT_FILENAME}")

