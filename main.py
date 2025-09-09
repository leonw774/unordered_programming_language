import argparse
import random
import tokenize

from collections import Counter

from pyprimesieve import primes_nth

# use non-whitespace printables
GREEK_EXCLUDE = {
    0x378, 0x379, 0x380, 0x381, 0x382, 0x383, 0x38b, 0x38d, 0x3a2
}
CYRILLIC_EXCLUDE = {
    0x483, 0x484, 0x485, 0x486, 0x487, 0x488, 0x489
}
ARMENIAN_EXCLUDE = {
    0x530, 0x557, 0x558, 0x58b, 0x58c
}
GREEK_EXTEND_EXCLUDE = {
    0x1f16, 0x1f17, 0x1f1e, 0x1f1f, 0x1f46, 0x1f47, 0x1f4e, 0x1f4f, 0x1f58,
    0x1f5a, 0x1f5c, 0x1f5e, 0x1f7e, 0x1f7f, 0x1fb5, 0x1fc5, 0x1fd4, 0x1fd5,
    0x1fdc, 0x1ff0, 0x1ff1, 0x1ff5, 0x1fff
}
ALPHABET = (
    # ASCII
    [chr(u) for u in range(0x21, 0x7f)]
    # Latin-1 Supplement
    + [chr(u) for u in range(0xa1, 0x100) if u != 0xad]
    # Latin Extended-A
    + [chr(u) for u in range(0x100, 0x180)]
    # Latin Extended-B
    + [chr(u) for u in range(0x180, 0x250)]
    # IPA Extensions
    + [chr(u) for u in range(0x250, 0x2af)]
    # Greek
    + [chr(u) for u in range(0x370, 0x400) if u not in GREEK_EXCLUDE]
    # Cyrillic
    + [chr(u) for u in range(0x400, 0x500) if u not in CYRILLIC_EXCLUDE]
    # Cyrillic Supplement
    + [chr(u) for u in range(0x500, 0x530)]
    # Armenian
    + [chr(u) for u in range(0x530, 0x590) if u not in ARMENIAN_EXCLUDE]
    # Latin Extended Additional
    + [chr(u) for u in range(0x1e00, 0x1f00)]
    # Greek Extended
    + [chr(u) for u in range(0x1f00, 0x1fff) if u not in GREEK_EXTEND_EXCLUDE]
    # Currency Symbols
    + [chr(u) for u in range(0x20a0, 0x20c1)]
    # Letterlike Symbols
    + [chr(u) for u in range(0x2100, 0x2150)]
    # Number Forms
    + [chr(u) for u in range(0x2150, 0x218c)]
    # Arrows & Mathematical Operators
    + [chr(u) for u in range(0x2190, 0x2300)]
    # Miscellaneous Technical
    + [chr(u) for u in range(0x2300, 0x2400)]
)
VEC_SIZE = len(ALPHABET)

def u4s_to_vec(xs: list[int]):
    vec = [1] * VEC_SIZE
    for i, x in enumerate(xs):
        vec[i % VEC_SIZE] *= primes_nth((i // VEC_SIZE) + 1) ** x
    return vec

def vec_to_u4s(vec: list[int]):
    xs = []
    i = 0
    while True:
        v = vec[i % VEC_SIZE]
        p = primes_nth((i // VEC_SIZE) + 1)
        x = 0
        while v % p == 0:
            v //= p
            x += 1
        if x == 0:
            break
        xs.append(x)
        i += 1
    return xs

def token_info_to_u4s(ttype: int, tstr: str) -> int:
    # encode type -> 3-bit numbers
    u4s = [ttype // 64, (ttype // 8) % 8, ttype % 8]
    # encode str -> 3-bit numbers
    u4s += [
        x
        for byte in tstr.encode()
        for x in [byte // 64, (byte // 8) % 8, byte % 8]
    ]
    # encode length -> 2-bit variable-length quantity encoding
    length_u4s = []
    length = (len(u4s) - 3) // 3 # the length of tstr in bytes
    if length == 0:
        length_u4s = [0]
    else:
        while length > 0:
            r = length % 4
            length //= 4
            length_u4s = [r] + length_u4s
    # add 4 to all lengths except the last one
    length_u4s = [x + 4 for x in length_u4s[:-1]] + [length_u4s[-1]]
    # finally, all add 1 so that there are no zero
    return [u + 1 for u in (length_u4s + u4s)]

def u4s_to_token_infos(u4s):
    i = 0
    token_infos = []
    while i < len(u4s):
        # decode length
        length = 0
        while True:
            val = u4s[i] - 1
            i += 1
            if val >= 4:
                length = length * 4 + (val - 4)
            else:
                length = length * 4 + val
                break
        # decode type
        ttype = (u4s[i] - 1) * 64 + (u4s[i+1] - 1) * 8 + (u4s[i+2] - 1)
        i += 3
        # decode string
        str_bytes = []
        for _ in range(length):
            byte = (u4s[i] - 1) * 64 + (u4s[i+1] - 1) * 8 + (u4s[i+2] - 1)
            str_bytes.append(byte)
            i += 3
        tstr = bytes(str_bytes).decode(errors='ignore')
        token_infos.append((ttype, tstr))
    return token_infos

def encode(token_infos: list[tokenize.TokenInfo]) -> str:
    # minimize
    mini_token_infos = []
    cur_indent_depth = 0
    for token_info in token_infos[1:]:
        if token_info.type == tokenize.NL:
            pass # remove redundent newlines
        elif token_info.type == tokenize.COMMENT:
            pass # remove comments
        elif token_info.type == tokenize.INDENT:
            new_indent = ' ' * (cur_indent_depth + 1)
            mini_token_infos.append((token_info.type, new_indent))
            cur_indent_depth += 1
        elif token_info.type == tokenize.DEDENT:
            mini_token_infos.append((token_info.type, ''))
            cur_indent_depth -= 1
        else:
            mini_token_infos.append((token_info.type, token_info.string))
    if debug_flag:
        print('tokens:', mini_token_infos)
    token_u4s = [
        n
        for ttype, tstr in mini_token_infos
        for n in token_info_to_u4s(ttype, tstr)
    ]
    if debug_flag:
        print('u4s:', token_u4s)
    vec = u4s_to_vec(token_u4s)
    if debug_flag:
        print('vector:', [n for n in vec if n != 1])
    chars_count = sum(n - 1 for n in vec)
    if debug_flag:
        print('char#:', chars_count)
    if chars_count > 1_000_000:
        print('result too large: output the vector instead')
        return repr(vec)
    # generate chars according to vec
    char_indices = [
        i
        for i, n in enumerate(vec) if n != 1
        for _ in range(n - 1)
    ]
    if chars_count > 100_000:
        print('result too large. output without shuffling the characters.')
    else:
        random.shuffle(char_indices)
    return ''.join(ALPHABET[i] for i in char_indices)

def decode(chars: str) -> list[tokenize.TokenInfo]:
    # count occurrences of each ALPHABET element
    counts = Counter([chars[i:i+2] for i in range(0, len(chars), 2)])
    vec = [counts.get(a, 0) + 1 for a in ALPHABET]
    if debug_flag:
        print('vector:', [n for n in vec if n != 1])
    token_u4s = vec_to_u4s(vec)
    if debug_flag:
        print('u4s:', token_u4s)
    mini_token_infos = u4s_to_token_infos(token_u4s)
    if debug_flag:
        print('tokens:', mini_token_infos)
    return mini_token_infos

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')

    subparser = parser.add_subparsers(dest='command')
    enc_parser = subparser.add_parser('enc')
    enc_parser.add_argument(
        'input_file',
        type=str
    )
    enc_parser.add_argument(
        'output_file',
        type=str
    )

    dec_parser = subparser.add_parser('dec')
    dec_parser.add_argument(
        'input_file',
        type=str
    )
    dec_parser.add_argument(
        'output_file',
        type=str
    )

    exec_parser = subparser.add_parser('exec')
    exec_parser.add_argument(
        'input_file',
        type=str
    )
    return parser.parse_args()

debug_flag = False

def main():
    args = parse_args()
    global debug_flag
    debug_flag = args.debug
    if debug_flag:
        print('alphabet count:', len(ALPHABET))
        print('alphabet:', ''.join(ALPHABET))
    mode = args.command
    if mode == 'enc':
        # read the input python content
        token_infos = []
        with open(args.input_file, 'rb') as f:
            token_infos = [token for token in tokenize.tokenize(f.readline)]
        chars = encode(token_infos)
        with open(args.output_file, 'w+', encoding='utf8') as f:
            f.write(chars)

    if mode == 'dec':
        with open(args.input_file, 'r', encoding='utf8') as f:
            chars = f.read()
        with open(args.output_file, 'w', encoding='utf8') as f:
            f.write(tokenize.untokenize(decode(chars)))

    if mode == 'exec':
        with open(args.input_file, 'r', encoding='utf8') as f:
            chars = f.read()
        exec(tokenize.untokenize(decode(chars)))

if __name__ == '__main__':
    main()
