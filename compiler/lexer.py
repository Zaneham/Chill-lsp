"""
CHILL Lexer
Based on ITU-T Recommendation Z.200 (1999)

Tokenizes CHILL source code into a stream of tokens.
"""

import re
from dataclasses import dataclass
from typing import Iterator, Optional, List
from enum import Enum, auto


class TokenType(Enum):
    """Token types for CHILL"""
    # Literals
    INTEGER = auto()
    REAL = auto()
    STRING = auto()
    CHAR = auto()
    BINARY = auto()
    HEX = auto()
    OCTAL = auto()

    # Identifiers and keywords
    IDENTIFIER = auto()
    KEYWORD = auto()
    BUILTIN = auto()

    # Operators
    PLUS = auto()          # +
    MINUS = auto()         # -
    STAR = auto()          # *
    SLASH = auto()         # /
    POWER = auto()         # **
    ASSIGN = auto()        # :=
    EQ = auto()            # =
    NE = auto()            # /=
    LT = auto()            # <
    GT = auto()            # >
    LE = auto()            # <=
    GE = auto()            # >=
    CONCAT = auto()        # //
    ARROW = auto()         # ->
    COLON = auto()         # :
    SEMICOLON = auto()     # ;
    COMMA = auto()         # ,
    DOT = auto()           # .
    LPAREN = auto()        # (
    RPAREN = auto()        # )
    LBRACKET = auto()      # [
    RBRACKET = auto()      # ]

    # Special
    NEWLINE = auto()
    COMMENT = auto()
    EOF = auto()
    ERROR = auto()


# Reserved words from ITU-T Z.200 Appendix III.1
KEYWORDS = {
    'ABSTRACT', 'ACCESS', 'AFTER', 'ALL', 'AND', 'ANDIF', 'ANY', 'ANY_ASSIGN',
    'ANY_DISCRETE', 'ANY_INT', 'ANY_REAL', 'ARRAY', 'ASSIGNABLE', 'ASSERT', 'AT',
    'BASED_ON', 'BEGIN', 'BIN', 'BODY', 'BOOLS', 'BUFFER', 'BY', 'CASE', 'CAUSE',
    'CHARS', 'CONSTR', 'CONTEXT', 'CONTINUE', 'CYCLE', 'DCL', 'DELAY', 'DESTR',
    'DO', 'DOWN', 'DYNAMIC', 'ELSE', 'ELSIF', 'END', 'ESAC', 'EVENT', 'EVER',
    'EXCEPTIONS', 'EXIT', 'FI', 'FINAL', 'FOR', 'FORBID', 'GENERAL', 'GENERIC',
    'GOTO', 'GRANT', 'IF', 'IMPLEMENTS', 'IN', 'INCOMPLETE', 'INIT', 'INLINE',
    'INOUT', 'INTERFACE', 'INVARIANT', 'LOC', 'MOD', 'MODE', 'MODULE', 'NEW',
    'NEWMODE', 'NONREF', 'NOT_ASSIGNABLE', 'NOPACK', 'NOT', 'OD', 'OF', 'ON',
    'OR', 'ORIF', 'OUT', 'PACK', 'POS', 'POST', 'POWERSET', 'PRE', 'PREFIXED',
    'PRIORITY', 'PROC', 'PROCESS', 'RANGE', 'READ', 'RECEIVE', 'REF', 'REGION',
    'REIMPLEMENT', 'REM', 'REMOTE', 'RESULT', 'RETURN', 'RETURNS', 'ROW', 'SEIZE',
    'SELF', 'SEND', 'SET', 'SIGNAL', 'SIMPLE', 'SPEC', 'START', 'STATIC', 'STEP',
    'STOP', 'STRUCT', 'SYN', 'SYNMODE', 'TASK', 'TEXT', 'THEN', 'THIS', 'TIMEOUT',
    'TO', 'UP', 'VARYING', 'WCHARS', 'WHILE', 'WITH', 'WTEXT', 'XOR'
}

# Predefined names from ITU-T Z.200 Appendix III.2
BUILTINS = {
    'ABS', 'ABSTIME', 'ALLOCATE', 'ARCCOS', 'ARCSIN', 'ARCTAN', 'ASSOCIATE',
    'ASSOCIATION', 'BOOL', 'CARD', 'CHAR', 'CONNECT', 'COS', 'CREATE', 'DAYS',
    'DELETE', 'DISCONNECT', 'DISSOCIATE', 'DURATION', 'EOLN', 'EXISTING', 'EXP',
    'EXPIRED', 'FALSE', 'FIRST', 'FLOAT', 'GETASSOCIATION', 'GETSTACK',
    'GETTEXTACCESS', 'GETTEXTINDEX', 'GETTEXTRECORD', 'GETUSAGE', 'HOURS',
    'INDEXABLE', 'INSTANCE', 'INT', 'INTTIME', 'ISASSOCIATED', 'LAST', 'LENGTH',
    'LN', 'LOG', 'LOWER', 'MAX', 'MILLISECS', 'MIN', 'MINUTES', 'MODIFY', 'NULL',
    'NUM', 'OUTOFFILE', 'PRED', 'PTR', 'READABLE', 'READONLY', 'READRECORD',
    'READTEXT', 'READWRITE', 'SAME', 'SECS', 'SEQUENCIBLE', 'SETTEXTACCESS',
    'SETTEXTINDEX', 'SETTEXTRECORD', 'SIN', 'SIZE', 'SQRT', 'SUCC', 'TAN',
    'TERMINATE', 'TIME', 'TRUE', 'UPPER', 'USAGE', 'VARIABLE', 'WAIT', 'WCHAR',
    'WHERE', 'WRITEABLE', 'WRITEONLY', 'WRITERECORD', 'WRITETEXT',
    # Implementation-defined
    'BYTE', 'UBYTE', 'UINT', 'LONG', 'ULONG', 'REAL', 'LONG_REAL',
    'SECONDS', 'MICROSECS'
}


@dataclass
class Token:
    """A single token from the source"""
    type: TokenType
    value: str
    line: int
    column: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.column})"


class LexerError(Exception):
    """Lexer error with location"""
    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"{message} at line {line}, column {column}")


class Lexer:
    """
    CHILL Lexer

    Tokenizes CHILL source code according to ITU-T Z.200.
    """

    def __init__(self, source: str, filename: str = "<input>"):
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

    def error(self, message: str) -> None:
        """Raise a lexer error at current position"""
        raise LexerError(message, self.line, self.column)

    def peek(self, offset: int = 0) -> str:
        """Look at character at current position + offset"""
        pos = self.pos + offset
        if pos >= len(self.source):
            return '\0'
        return self.source[pos]

    def advance(self) -> str:
        """Consume and return current character"""
        if self.pos >= len(self.source):
            return '\0'
        char = self.source[self.pos]
        self.pos += 1
        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def skip_whitespace(self) -> None:
        """Skip spaces, tabs, and newlines"""
        while self.peek() in ' \t\r\n':
            self.advance()

    def skip_comment(self) -> bool:
        """Skip block or line comments, return True if comment was skipped"""
        if self.peek() == '/' and self.peek(1) == '*':
            # Block comment /* ... */
            self.advance()  # /
            self.advance()  # *
            while not (self.peek() == '*' and self.peek(1) == '/'):
                if self.peek() == '\0':
                    self.error("Unterminated block comment")
                self.advance()
            self.advance()  # *
            self.advance()  # /
            return True
        elif self.peek() == '-' and self.peek(1) == '-':
            # Line comment -- ...
            while self.peek() not in '\n\0':
                self.advance()
            return True
        return False

    def read_string(self) -> Token:
        """Read a string literal 'xxx' or \"xxx\""""
        start_line = self.line
        start_col = self.column
        quote = self.advance()  # ' or "
        value = ""

        while True:
            char = self.peek()
            if char == '\0':
                self.error("Unterminated string literal")
            if char == quote:
                if self.peek(1) == quote:
                    # Escaped quote
                    value += quote
                    self.advance()
                    self.advance()
                else:
                    # End of string
                    self.advance()
                    break
            else:
                value += char
                self.advance()

        return Token(TokenType.STRING, value, start_line, start_col)

    def read_char_literal(self) -> Token:
        """Read a character literal C'x'"""
        start_line = self.line
        start_col = self.column
        self.advance()  # C
        if self.peek() != "'":
            self.error("Expected ' after C in character literal")
        self.advance()  # '
        char = self.advance()
        if self.peek() != "'":
            self.error("Expected closing ' in character literal")
        self.advance()  # '
        return Token(TokenType.CHAR, char, start_line, start_col)

    def read_number(self) -> Token:
        """Read an integer or real number"""
        start_line = self.line
        start_col = self.column
        value = ""

        # Read integer part
        while self.peek().isdigit():
            value += self.advance()

        # Check for real number
        if self.peek() == '.' and self.peek(1).isdigit():
            value += self.advance()  # .
            while self.peek().isdigit():
                value += self.advance()
            # Check for exponent
            if self.peek().upper() == 'E':
                value += self.advance()
                if self.peek() in '+-':
                    value += self.advance()
                while self.peek().isdigit():
                    value += self.advance()
            return Token(TokenType.REAL, value, start_line, start_col)

        return Token(TokenType.INTEGER, value, start_line, start_col)

    def read_based_literal(self) -> Token:
        """Read B'...', H'...', or O'...' literals"""
        start_line = self.line
        start_col = self.column
        base = self.advance().upper()  # B, H, or O

        if self.peek() != "'":
            # Not a based literal, treat as identifier
            self.pos -= 1
            self.column -= 1
            return self.read_identifier()

        self.advance()  # '
        value = ""

        if base == 'B':
            while self.peek() in '01':
                value += self.advance()
            token_type = TokenType.BINARY
        elif base == 'H':
            while self.peek() in '0123456789ABCDEFabcdef':
                value += self.advance()
            token_type = TokenType.HEX
        elif base == 'O':
            while self.peek() in '01234567':
                value += self.advance()
            token_type = TokenType.OCTAL
        else:
            self.error(f"Unknown base literal type: {base}")

        if self.peek() != "'":
            self.error(f"Expected closing ' in {base} literal")
        self.advance()  # '

        return Token(token_type, value, start_line, start_col)

    def read_identifier(self) -> Token:
        """Read an identifier or keyword"""
        start_line = self.line
        start_col = self.column
        value = ""

        while self.peek().isalnum() or self.peek() == '_':
            value += self.advance()

        upper_value = value.upper()

        if upper_value in KEYWORDS:
            return Token(TokenType.KEYWORD, upper_value, start_line, start_col)
        elif upper_value in BUILTINS:
            return Token(TokenType.BUILTIN, upper_value, start_line, start_col)
        else:
            return Token(TokenType.IDENTIFIER, value, start_line, start_col)

    def read_operator(self) -> Token:
        """Read an operator or punctuation"""
        start_line = self.line
        start_col = self.column
        char = self.peek()

        # Two-character operators
        two_char = self.source[self.pos:self.pos + 2]
        if two_char == ':=':
            self.advance()
            self.advance()
            return Token(TokenType.ASSIGN, ':=', start_line, start_col)
        elif two_char == '/=':
            self.advance()
            self.advance()
            return Token(TokenType.NE, '/=', start_line, start_col)
        elif two_char == '<=':
            self.advance()
            self.advance()
            return Token(TokenType.LE, '<=', start_line, start_col)
        elif two_char == '>=':
            self.advance()
            self.advance()
            return Token(TokenType.GE, '>=', start_line, start_col)
        elif two_char == '//':
            self.advance()
            self.advance()
            return Token(TokenType.CONCAT, '//', start_line, start_col)
        elif two_char == '**':
            self.advance()
            self.advance()
            return Token(TokenType.POWER, '**', start_line, start_col)
        elif two_char == '->':
            self.advance()
            self.advance()
            return Token(TokenType.ARROW, '->', start_line, start_col)

        # Single-character operators
        self.advance()
        if char == '+':
            return Token(TokenType.PLUS, '+', start_line, start_col)
        elif char == '-':
            return Token(TokenType.MINUS, '-', start_line, start_col)
        elif char == '*':
            return Token(TokenType.STAR, '*', start_line, start_col)
        elif char == '/':
            return Token(TokenType.SLASH, '/', start_line, start_col)
        elif char == '=':
            return Token(TokenType.EQ, '=', start_line, start_col)
        elif char == '<':
            return Token(TokenType.LT, '<', start_line, start_col)
        elif char == '>':
            return Token(TokenType.GT, '>', start_line, start_col)
        elif char == ':':
            return Token(TokenType.COLON, ':', start_line, start_col)
        elif char == ';':
            return Token(TokenType.SEMICOLON, ';', start_line, start_col)
        elif char == ',':
            return Token(TokenType.COMMA, ',', start_line, start_col)
        elif char == '.':
            return Token(TokenType.DOT, '.', start_line, start_col)
        elif char == '(':
            return Token(TokenType.LPAREN, '(', start_line, start_col)
        elif char == ')':
            return Token(TokenType.RPAREN, ')', start_line, start_col)
        elif char == '[':
            return Token(TokenType.LBRACKET, '[', start_line, start_col)
        elif char == ']':
            return Token(TokenType.RBRACKET, ']', start_line, start_col)
        else:
            self.error(f"Unexpected character: {char!r}")

    def next_token(self) -> Token:
        """Get the next token from the source"""
        while True:
            self.skip_whitespace()

            # Skip comments
            if self.skip_comment():
                continue

            if self.pos >= len(self.source):
                return Token(TokenType.EOF, '', self.line, self.column)

            char = self.peek()

            # String literals
            if char in '"\'':
                return self.read_string()

            # Character literal C'x'
            if char == 'C' and self.peek(1) == "'":
                return self.read_char_literal()

            # Based literals B'...', H'...', O'...'
            if char in 'BHObho' and self.peek(1) == "'":
                return self.read_based_literal()

            # Numbers
            if char.isdigit():
                return self.read_number()

            # Identifiers and keywords
            if char.isalpha() or char == '_':
                return self.read_identifier()

            # Operators and punctuation
            return self.read_operator()

    def tokenize(self) -> List[Token]:
        """Tokenize the entire source, returning list of tokens"""
        tokens = []
        while True:
            token = self.next_token()
            tokens.append(token)
            if token.type == TokenType.EOF:
                break
        return tokens


def tokenize(source: str, filename: str = "<input>") -> List[Token]:
    """Convenience function to tokenize source code"""
    lexer = Lexer(source, filename)
    return lexer.tokenize()


# Test
if __name__ == '__main__':
    test_code = '''
    MODULE example;

    /* This is a comment */
    -- This is also a comment

    NEWMODE counter = RANGE(0:65535);
    NEWMODE status = SET(idle, active, error);

    SYN max_size = 100;

    DCL count counter := 0;
    DCL name CHARS(30) := 'Hello, CHILL!';
    DCL flags BOOLS(8) := B'10101010';
    DCL code INT := H'FF';

    handler: PROC(input INT) RETURNS(INT);
        DCL result INT;
        result := input * 2 + 1;
        IF result > max_size THEN
            result := max_size;
        FI;
        RETURN result;
    END handler;

    END example;
    '''

    print("=== CHILL Lexer Test ===\n")
    try:
        tokens = tokenize(test_code)
        for tok in tokens:
            print(tok)
        print(f"\nTotal tokens: {len(tokens)}")
    except LexerError as e:
        print(f"Lexer error: {e}")
