# unordered_programming_language

This thing encodes Python 3 code into a unordered multi-set representation and can decode it back and execute it.

Inspired by [Can a language have free phoneme order?](https://www.youtube.com/watch?v=0a27tS3ltFc) by Kat Mistberg

## Usage

`main.py enc input_file output_file`

- Encode the Python 3 code from `input_file` to uncodered characters and write it to `output_file`.

`main.py dec input_file output_file`

- Decode the uncodered characters from `input_file` to Python 3 code and write it to `output_file`.

`main.py exec input_file`

- Execute the uncodered characters from `input_file` after decoded it to Python 3 code.
