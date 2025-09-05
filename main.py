import argparse
import random
import string
import tokenize

from collections import Counter
from itertools import product, zip_longest

from pyprimesieve import primes_nth

# get all non-whitespace printable chars in a "messy" order
NON_WS_PRINTABLES = [
    c
    for cs in zip_longest(
        string.ascii_letters, reversed(string.digits), string.punctuation
    )
    for c in cs if c is not None
]
# use the product of our "messy" printables, also in "messy" order
CHAR_PRODUCT = [l + r for l, r in product(NON_WS_PRINTABLES, repeat=2)]
ALPHABET = [
    p
    for ps in zip_longest(
        CHAR_PRODUCT[:2048], CHAR_PRODUCT[2048:4096], CHAR_PRODUCT[4096:6144],
        CHAR_PRODUCT[6144:]
    )
    for p in ps if p is not None
]
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
    # print(mini_token_infos)
    token_u4s = [
        n
        for ttype, tstr in mini_token_infos
        for n in token_info_to_u4s(ttype, tstr)
    ]
    # print(token_u4s)
    vec = u4s_to_vec(token_u4s)
    # print(vec)
    # generate pairs accordding to vec
    char_lists = [
        c
        for i, n in enumerate(vec) if n != 1
        for c in ([ALPHABET[i]] * (n - 1))
    ]
    random.shuffle(char_lists)
    return len(token_u4s), (''.join(char_lists))

def decode(chars: str) -> list[tokenize.TokenInfo]:
    # count occurrences of each ALPHABET element
    counts = Counter([chars[i:i+2] for i in range(0, len(chars), 2)])
    vec = [counts.get(a, 0) + 1 for a in ALPHABET]
    # print(vec)
    token_u4s = vec_to_u4s(vec)
    # print(token_u4s)
    mini_token_infos = u4s_to_token_infos(token_u4s)
    # print(mini_token_infos)
    return mini_token_infos

def parse_args():
    parser = argparse.ArgumentParser()
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

def main():
    args = parse_args()
    mode = args.command
    if mode == 'enc':
        # read the input python content
        token_infos = []
        with open(args.input_file, 'rb') as f:
            token_infos = [token for token in tokenize.tokenize(f.readline)]
        length, chars = encode(token_infos)
        with open(args.output_file, 'w+', encoding='utf8') as f:
            f.write(''.join(chars))

    if mode == 'dec':
        with open(args.input_file, 'r', encoding='utf8') as f:
            chars = f.read()
        with open(args.output_file, 'w', encoding='utf8') as f:
            f.write(tokenize.untokenize(decode(chars)))

    if mode == 'exec':
        with open(args.input_file, 'r', encoding='utf8') as f:
            chars = f.read()
        exec(tokenize.untokenize(decode(chars)))

if __name__ == "__main__":
    main()
