import argparse
import itertools
import random
import string
import tokenize

from collections import Counter

from pyprimesieve import primes_nth

NON_WS_PRINTABLES = string.digits + string.ascii_letters + string.punctuation
# ALPHABET = NON_WS_PRINTABLES
ALPHABET = [l + r for l, r in itertools.product(NON_WS_PRINTABLES, repeat=2)]
VEC_SIZE = len(ALPHABET)

def u4s_to_vec(xs: list[int]):
    vec = [1] * VEC_SIZE
    for i, x in enumerate(xs):
        vec[i % VEC_SIZE] *= primes_nth((i // VEC_SIZE) + 1) ** x
    return vec

def vec_to_u4s(vec: list[int], length: int):
    xs = []
    for i in range(length):
        v = vec[i % VEC_SIZE]
        p = primes_nth((i // VEC_SIZE) + 1)
        x = 0
        while v % p == 0:
            v //= p
            x += 1
        xs.append(x)
    return xs


def token_info_to_u4s(ttype: int, tstr: str) -> int:
    # encode type -> uint4
    u4s = [ttype // 16, ttype % 16]
    # encode str -> uint4
    u4s += [
        x
        for byte in tstr.encode()
        for x in [byte // 16, byte % 16]
    ]
    # encode length -> 3-bit variable-length quantity encoding
    length_u4s = []
    length = len(u4s) - 2 # because type always use 2
    if length == 0:
        length_u4s = [0]
    else:
        while length > 0:
            r = length % 8
            length //= 8
            length_u4s = [r] + length_u4s
    # add 8 to all lengths except the last one
    length_u4s = [x + 8 for x in length_u4s[:-1]] + [length_u4s[-1]]
    return [s for s in (length_u4s + u4s)]

def u4s_to_token_infos(u4s):
    i = 0
    token_infos = []
    while i < len(u4s):
        # decode length
        length = 0
        while True:
            val = u4s[i]
            i += 1
            if val >= 8:
                length = length * 8 + (val - 8)
            else:
                length = length * 8 + val
                break
        # decode type
        ttype = u4s[i] * 16 + u4s[i+1]
        i += 2
        # decode string
        str_bytes = []
        for k in range(length):
            b = u4s[i]
            i += 1
            if k % 2 == 0:
                str_bytes.append(b * 16)
            else:
                str_bytes[-1] += b
        tstr = bytes(str_bytes).decode(errors='ignore')
        token_infos.append((ttype, tstr))
    return token_infos

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

def decode(length: int, chars: str) -> list[tokenize.TokenInfo]:
    # count occurrences of each ALPHABET element
    counts = Counter([chars[i:i+2] for i in range(0, len(chars), 2)])
    vec = [counts.get(a, 0) + 1 for a in ALPHABET]
    # print(vec)
    token_u4s = vec_to_u4s(vec, length)
    # print(token_u4s)
    mini_token_infos = u4s_to_token_infos(token_u4s)
    # print(mini_token_infos)
    return mini_token_infos

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
            f.write(repr(length) + '\n')
            f.write(''.join(chars))

    if mode == 'dec':
        with open(args.input_file, 'r', encoding='utf8') as f:
            length = int(f.readline())
            chars = f.readline()
        with open(args.output_file, 'w', encoding='utf8') as f:
            f.write(tokenize.untokenize(decode(length, chars)))

    if mode == 'exec':
        with open(args.input_file, 'r', encoding='utf8') as f:
            length = int(f.readline())
            chars = f.readline()
        exec(tokenize.untokenize(decode(length, chars)))

if __name__ == "__main__":
    main()
