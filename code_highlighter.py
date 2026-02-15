import re

def highlight_code(code, language):
    """
    Generate a simple HTML-based syntax highlighting for different programming languages.
    """
    # Define color scheme
    colors = {
        'keyword': '#007020',    # dark green for keywords
        'string': '#4070a0',     # blue for strings
        'comment': '#60a0b0',    # teal for comments
        'default': '#000000'     # black for default text
    }

    # Language-specific keyword lists and comment patterns
    language_rules = {
        'Python': {
            'keywords': ['def', 'class', 'print', 'import', 'from', 'if', 'else', 'elif', 'for', 'while', 'return', 'in', 'and', 'or', 'not'],
            'comment_pattern': r'(#.*?)(\n|$)',
            'string_pattern': r'([\'"])(.*?)\1'
        },
        'C++': {
            'keywords': ['int', 'void', 'class', 'return', 'using', 'namespace', 'std', 'const', 'auto'],
            'comment_pattern': r'(//.*?)(\n|$)|(\/\*.*?\*\/)',
            'string_pattern': r'(")(.*?)"'
        },
        'Rust': {
            'keywords': ['fn', 'let', 'mut', 'return', 'pub', 'use', 'mod', 'impl'],
            'comment_pattern': r'(//.*?)(\n|$)|(\/\*.*?\*\/)',
            'string_pattern': r'(")(.*?)"'
        },
        'JavaScript': {
            'keywords': ['function', 'const', 'let', 'var', 'if', 'else', 'return', 'class', 'import', 'export'],
            'comment_pattern': r'(\/\/.*?)(\n|$)|(\/\*.*?\*\/)',
            'string_pattern': r'([\'"])(.*?)\1'
        },
        'PHP': {
            'keywords': ['function', 'return', 'echo', 'if', 'else', 'while', 'for', 'class', 'public', 'private'],
            'comment_pattern': r'(\/\/.*?)(\n|$)|(\/\*.*?\*\/)|(\#.*?)(\n|$)',
            'string_pattern': r'([\'"])(.*?)\1'
        }
    }

    # Use default rules if language not found
    rules = language_rules.get(language, {
        'keywords': [],
        'comment_pattern': r'(#.*?)(\n|$)',
        'string_pattern': r'([\'"])(.*?)\1'
    })

    # Escape HTML special characters first
    code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    # Highlight comments
    code = re.sub(rules['comment_pattern'],
                  lambda m: f'<span style="color: {colors["comment"]};">{m.group(0)}</span>',
                  code,
                  flags=re.DOTALL)

    # Highlight strings
    code = re.sub(rules['string_pattern'],
                  lambda m: f'<span style="color: {colors["string"]};">{m.group(0)}</span>',
                  code)

    # Highlight keywords
    for keyword in rules['keywords']:
        # Use word boundaries to match whole words
        code = re.sub(rf'\b{keyword}\b',
                      f'<span style="color: {colors["keyword"]};">{keyword}</span>',
                      code)

    return code

def generate_language_code_highlights():
    """
    Generate code highlights for multiple programming languages.
    """
    language_codes = {
        'Python': '''def hello_world():
    print('Hello, World!')

hello_world()''',
        'C++': '''#include <iostream>
using namespace std;

int main() {
    cout << "Hello, World!" << endl;
    return 0;
}''',
        'Rust': '''fn main() {
    println!("Hello, World!");
}''',
        'JavaScript': '''function helloWorld() {
    console.log("Hello, World!");
}

helloWorld();''',
        'PHP': '''<?php
function hello_world() {
    echo "Hello, World!";
}

hello_world();
?>'''
    }

    # Highlight the code for each language
    highlighted_codes = {}
    for lang, code in language_codes.items():
        highlighted_codes[lang] = highlight_code(code, lang)

    return highlighted_codes