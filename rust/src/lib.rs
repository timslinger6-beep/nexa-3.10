use std::fmt;

#[derive(Debug, Clone, PartialEq)]
pub enum TokenType {
    Number,
    String,
    Character,
    Identifier,
    Keyword,

    Plus,
    Minus,
    Star,
    Slash,
    Percent,
    Caret,
    StarStar,

    Equal,
    EqualEqual,
    NotEqual,
    Less,
    LessEqual,
    Greater,
    GreaterEqual,

    LogicalAnd,
    LogicalOr,
    LogicalNot,

    BitAnd,
    BitOr,
    BitXor,
    BitNot,

    ShiftLeft,
    ShiftRight,

    PlusEqual,
    MinusEqual,
    StarEqual,
    SlashEqual,
    PercentEqual,

    BitAndEqual,
    BitOrEqual,
    BitXorEqual,
    ShiftLeftEqual,
    ShiftRightEqual,

    Increment,
    Decrement,

    Arrow,
    FatArrow,

    LeftParen,
    RightParen,
    LeftBracket,
    RightBracket,
    LeftBrace,
    RightBrace,

    Comma,
    Dot,
    Semicolon,
    Colon,

    Question,
    At,
    Hash,

    Eof,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Token {
    pub token_type: TokenType,
    pub text: String,
    pub position: usize,
}

impl Token {
    fn new(token_type: TokenType, text: &str, position: usize) -> Self {
        Self {
            token_type,
            text: text.to_string(),
            position,
        }
    }
}

#[derive(Debug)]
pub struct LexerError {
    pub message: String,
    pub position: usize,
}

impl fmt::Display for LexerError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{} bei Position {}", self.message, self.position)
    }
}

fn is_keyword(text: &str) -> bool {
    matches!(
        text,
        "let" | "var" | "const" | "print" | "static" | "global" | "local"
        | "readonly" | "final" | "mutable" | "immutable" | "shared"
        | "persistent" | "temporary" | "volatile" | "atomic"
        | "constant" | "variable" | "alias" | "extern" | "inline"
        | "abstract" | "sealed" | "open" | "partial" | "unsafe"

        | "int" | "int8" | "int16" | "int32" | "int64" | "int128"
        | "uint8" | "uint16" | "uint32" | "uint64" | "uint128"
        | "float" | "float16" | "float32" | "float64" | "decimal"
        | "bigint" | "complex" | "rational" | "byte" | "bit" | "char"
        | "string" | "text" | "bool" | "object" | "any" | "auto"
        | "infer" | "optional" | "required" | "unknown" | "never"
        | "array" | "list" | "set" | "map" | "dict" | "record"
        | "tuple" | "vector" | "matrix" | "tensor" | "grid"
        | "tree" | "graph" | "stack" | "queue" | "heap" | "buffer"
        | "stream" | "channel" | "iterator" | "generator"
        | "sequence" | "collection" | "dictionary" | "pair" | "triple"
        | "range" | "slice" | "view" | "span" | "union" | "variant"
        | "result" | "success" | "failure" | "errorvalue"
        | "keyvalue" | "node" | "edge" | "property" | "field"
        | "attribute" | "metadata" | "schema" | "shape" | "dimension"
        | "unit" | "measure" | "currency" | "percentage"
        | "timestamp" | "duration" | "type" | "newtype" | "protocol"

        | "true" | "false" | "null" | "none"

        | "if" | "else" | "elseif" | "then"
        | "while" | "loop" | "repeat" | "for" | "foreach" | "in"
        | "break" | "continue" | "return" | "yield"
        | "switch" | "case" | "default" | "match" | "when"
        | "otherwise" | "unless" | "until" | "fallthrough"
        | "select" | "where" | "guard" | "require" | "ensure"
        | "assert" | "verify" | "check" | "validate" | "invariant"
        | "precondition" | "postcondition" | "contract"

        | "function" | "fn" | "lambda" | "closure" | "callback"
        | "method" | "getter" | "setter" | "constructor" | "destructor"
        | "delegate" | "procedure" | "macro" | "operator" | "extension"
        | "coroutine" | "async" | "await" | "defer" | "spawn" | "task"

        | "class" | "struct" | "enum" | "interface" | "trait"
        | "new" | "self" | "this" | "super" | "base" | "extends"
        | "implements" | "virtual" | "override"
        | "public" | "private" | "protected" | "internal"
        | "instance" | "prototype" | "inherits" | "owns"

        | "try" | "catch" | "finally" | "throw" | "panic" | "abort"
        | "recover" | "retry" | "error" | "ignore" | "suppress"
        | "checkpoint" | "rollback" | "transaction" | "commit"

        | "import" | "export" | "module" | "package" | "namespace"
        | "from" | "as" | "include" | "using" | "library"

        | "is" | "cast" | "convert" | "typeof" | "sizeof"
        | "nameof" | "implicit" | "explicit"

        | "and" | "or" | "not" | "xor" | "oneof" | "allof" | "anyof"
        | "noneof" | "every" | "some" | "only" | "except"

        | "lock" | "unlock" | "mutex" | "semaphore" | "parallel"
        | "concurrent" | "synchronized" | "atomicblock"
        | "deadlock" | "race"

        | "begin" | "end" | "start" | "continuewith" | "finish"
        | "complete" | "next" | "previous" | "first" | "last"
        | "current" | "nextvalue" | "previousvalue"

        | "allow" | "deny" | "grant" | "revoke" | "protect"
        | "secure" | "secret" | "token" | "permission"

        | "infinity" | "nan" | "undefined" | "optionalvalue"
        | "either" | "choose" | "branch" | "fork" | "join"
        | "merge" | "split" | "chain" | "pipe" | "flow" | "route"
        | "target" | "source" | "destination" | "input" | "output"
    )
}

pub fn lex(source: &str) -> Result<Vec<Token>, LexerError> {
    let chars: Vec<char> = source.chars().collect();
    let mut tokens = Vec::new();
    let mut pos = 0;

    while pos < chars.len() {
        let c = chars[pos];

        if c.is_whitespace() {
            pos += 1;
            continue;
        }

        // Kommentare
        if c == '/' && pos + 1 < chars.len() && chars[pos + 1] == '/' {
            pos += 2;
            while pos < chars.len() && chars[pos] != '\n' {
                pos += 1;
            }
            continue;
        }

        if c == '/' && pos + 1 < chars.len() && chars[pos + 1] == '*' {
            let start = pos;
            pos += 2;

            let mut closed = false;

            while pos + 1 < chars.len() {
                if chars[pos] == '*' && chars[pos + 1] == '/' {
                    pos += 2;
                    closed = true;
                    break;
                }
                pos += 1;
            }

            if !closed {
                return Err(LexerError {
                    message: "Unbeendeter Block-Kommentar".to_string(),
                    position: start,
                });
            }

            continue;
        }

        // Zahlen
        if c.is_ascii_digit() {
            let start = pos;

            if c == '0' && pos + 1 < chars.len() {
                match chars[pos + 1] {
                    'b' | 'B' => {
                        pos += 2;
                        let digits_start = pos;

                        while pos < chars.len()
                            && (chars[pos] == '0' || chars[pos] == '1')
                        {
                            pos += 1;
                        }

                        if pos == digits_start {
                            return Err(LexerError {
                                message: "Ungültige Binärzahl".to_string(),
                                position: start,
                            });
                        }

                        let text: String = chars[start..pos].iter().collect();
                        tokens.push(Token::new(TokenType::Number, &text, start));
                        continue;
                    }

                    'x' | 'X' => {
                        pos += 2;
                        let digits_start = pos;

                        while pos < chars.len()
                            && chars[pos].is_ascii_hexdigit()
                        {
                            pos += 1;
                        }

                        if pos == digits_start {
                            return Err(LexerError {
                                message: "Ungültige Hexadezimalzahl".to_string(),
                                position: start,
                            });
                        }

                        let text: String = chars[start..pos].iter().collect();
                        tokens.push(Token::new(TokenType::Number, &text, start));
                        continue;
                    }

                    'o' | 'O' => {
                        pos += 2;
                        let digits_start = pos;

                        while pos < chars.len()
                            && matches!(chars[pos], '0'..='7')
                        {
                            pos += 1;
                        }

                        if pos == digits_start {
                            return Err(LexerError {
                                message: "Ungültige Oktalzahl".to_string(),
                                position: start,
                            });
                        }

                        let text: String = chars[start..pos].iter().collect();
                        tokens.push(Token::new(TokenType::Number, &text, start));
                        continue;
                    }

                    _ => {}
                }
            }

            while pos < chars.len() && chars[pos].is_ascii_digit() {
                pos += 1;
            }

            if pos + 1 < chars.len()
                && chars[pos] == '.'
                && chars[pos + 1].is_ascii_digit()
            {
                pos += 1;

                while pos < chars.len() && chars[pos].is_ascii_digit() {
                    pos += 1;
                }
            }

            let text: String = chars[start..pos].iter().collect();
            tokens.push(Token::new(TokenType::Number, &text, start));
            continue;
        }

        // String / Character
        if c == '"' || c == '\'' {
            let quote = c;
            let start = pos;
            pos += 1;

            let mut value = String::new();
            let mut closed = false;

            while pos < chars.len() {
                let current = chars[pos];

                if current == quote {
                    pos += 1;
                    closed = true;
                    break;
                }

                if current == '\n' {
                    return Err(LexerError {
                        message: "String/Zeichen darf nicht über mehrere Zeilen gehen".to_string(),
                        position: start,
                    });
                }

                if current == '\\' {
                    pos += 1;

                    if pos >= chars.len() {
                        return Err(LexerError {
                            message: "Unvollständige Escape-Sequenz".to_string(),
                            position: pos - 1,
                        });
                    }

                    let escaped = chars[pos];

                    match escaped {
                        'n' => value.push('\n'),
                        'r' => value.push('\r'),
                        't' => value.push('\t'),
                        '"' => value.push('"'),
                        '\'' => value.push('\''),
                        '\\' => value.push('\\'),
                        '0' => value.push('\0'),
                        _ => {
                            return Err(LexerError {
                                message: format!(
                                    "Unbekannte Escape-Sequenz '\\{}'",
                                    escaped
                                ),
                                position: pos - 1,
                            });
                        }
                    }

                    pos += 1;
                    continue;
                }

                value.push(current);
                pos += 1;
            }

            if !closed {
                return Err(LexerError {
                    message: "Unbeendeter String/Char".to_string(),
                    position: start,
                });
            }

            let token_type = if quote == '"' {
                TokenType::String
            } else {
                if value.chars().count() != 1 {
                    return Err(LexerError {
                        message: "Char-Literal muss genau ein Zeichen enthalten".to_string(),
                        position: start,
                    });
                }

                TokenType::Character
            };

            tokens.push(Token {
                token_type,
                text: value,
                position: start,
            });

            continue;
        }

        // Identifier / Keywords
        if c.is_alphabetic() || c == '_' {
            let start = pos;
            pos += 1;

            while pos < chars.len()
                && (chars[pos].is_alphanumeric() || chars[pos] == '_')
            {
                pos += 1;
            }

            let text: String = chars[start..pos].iter().collect();

            let token_type = if is_keyword(&text) {
                TokenType::Keyword
            } else {
                TokenType::Identifier
            };

            tokens.push(Token::new(token_type, &text, start));
            continue;
        }

        let start = pos;

        let three = if pos + 2 < chars.len() {
            Some([chars[pos], chars[pos + 1], chars[pos + 2]])
        } else {
            None
        };

        if three == Some(['<', '<', '=']) {
            tokens.push(Token::new(TokenType::ShiftLeftEqual, "<<=", start));
            pos += 3;
            continue;
        }

        if three == Some(['>', '>', '=']) {
            tokens.push(Token::new(TokenType::ShiftRightEqual, ">>=", start));
            pos += 3;
            continue;
        }

        if pos + 1 < chars.len() {
            let two = [chars[pos], chars[pos + 1]];

            let token_type = match two {
                ['=', '='] => Some(TokenType::EqualEqual),
                ['!', '='] => Some(TokenType::NotEqual),
                ['<', '='] => Some(TokenType::LessEqual),
                ['>', '='] => Some(TokenType::GreaterEqual),

                ['&', '&'] => Some(TokenType::LogicalAnd),
                ['|', '|'] => Some(TokenType::LogicalOr),

                ['<', '<'] => Some(TokenType::ShiftLeft),
                ['>', '>'] => Some(TokenType::ShiftRight),

                ['+', '='] => Some(TokenType::PlusEqual),
                ['-', '='] => Some(TokenType::MinusEqual),
                ['*', '='] => Some(TokenType::StarEqual),
                ['/', '='] => Some(TokenType::SlashEqual),
                ['%', '='] => Some(TokenType::PercentEqual),

                ['&', '='] => Some(TokenType::BitAndEqual),
                ['|', '='] => Some(TokenType::BitOrEqual),
                ['^', '='] => Some(TokenType::BitXorEqual),

                ['+', '+'] => Some(TokenType::Increment),
                ['-', '-'] => Some(TokenType::Decrement),

                ['-', '>'] => Some(TokenType::Arrow),
                ['=', '>'] => Some(TokenType::FatArrow),

                ['*', '*'] => Some(TokenType::StarStar),

                _ => None,
            };

            if let Some(token_type) = token_type {
                let text: String = chars[pos..pos + 2].iter().collect();
                tokens.push(Token::new(token_type, &text, start));
                pos += 2;
                continue;
            }
        }

        let token_type = match c {
            '+' => TokenType::Plus,
            '-' => TokenType::Minus,
            '*' => TokenType::Star,
            '/' => TokenType::Slash,
            '%' => TokenType::Percent,
            '=' => TokenType::Equal,
            '<' => TokenType::Less,
            '>' => TokenType::Greater,
            '!' => TokenType::LogicalNot,

            '&' => TokenType::BitAnd,
            '|' => TokenType::BitOr,

            // Nexa verwendet ^ als CARET/Potenzoperator.
            '^' => TokenType::Caret,

            '~' => TokenType::BitNot,

            '(' => TokenType::LeftParen,
            ')' => TokenType::RightParen,
            '[' => TokenType::LeftBracket,
            ']' => TokenType::RightBracket,
            '{' => TokenType::LeftBrace,
            '}' => TokenType::RightBrace,

            ',' => TokenType::Comma,
            '.' => TokenType::Dot,
            ';' => TokenType::Semicolon,
            ':' => TokenType::Colon,

            '?' => TokenType::Question,
            '@' => TokenType::At,
            '#' => TokenType::Hash,

            _ => {
                return Err(LexerError {
                    message: format!("Unbekanntes Zeichen '{}'", c),
                    position: pos,
                });
            }
        };

        let text: String = chars[pos..pos + 1].iter().collect();
        tokens.push(Token::new(token_type, &text, start));
        pos += 1;
    }

    tokens.push(Token::new(TokenType::Eof, "", pos));

    Ok(tokens)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_nexa_rust_kern() {
        assert_eq!("Nexa Rust-Kern funktioniert!", "Nexa Rust-Kern funktioniert!");
    }

    #[test]
    fn test_lexer() {
        let tokens = lex("let x = 42").unwrap();

        assert_eq!(tokens[0].token_type, TokenType::Keyword);
        assert_eq!(tokens[1].token_type, TokenType::Identifier);
        assert_eq!(tokens[1].text, "x");
        assert_eq!(tokens[2].token_type, TokenType::Equal);
        assert_eq!(tokens[3].token_type, TokenType::Number);
        assert_eq!(tokens[3].text, "42");
        assert_eq!(tokens[4].token_type, TokenType::Eof);
    }

    #[test]
    fn test_operators() {
        let tokens = lex(
            "== != <= >= && || & | ^ ~ << >> += -= *= /= %= &= |= ^= ++ -- -> => **"
        )
        .unwrap();

        assert_eq!(tokens[0].token_type, TokenType::EqualEqual);
        assert_eq!(tokens[1].token_type, TokenType::NotEqual);
        assert_eq!(tokens[2].token_type, TokenType::LessEqual);
        assert_eq!(tokens[3].token_type, TokenType::GreaterEqual);
        assert_eq!(tokens[4].token_type, TokenType::LogicalAnd);
        assert_eq!(tokens[5].token_type, TokenType::LogicalOr);
        assert_eq!(tokens[6].token_type, TokenType::BitAnd);
        assert_eq!(tokens[7].token_type, TokenType::BitOr);
        assert_eq!(tokens[8].token_type, TokenType::Caret);
        assert_eq!(tokens[9].token_type, TokenType::BitNot);
        assert_eq!(tokens[10].token_type, TokenType::ShiftLeft);
        assert_eq!(tokens[11].token_type, TokenType::ShiftRight);
        assert_eq!(tokens[12].token_type, TokenType::PlusEqual);
        assert_eq!(tokens[13].token_type, TokenType::MinusEqual);
        assert_eq!(tokens[14].token_type, TokenType::StarEqual);
        assert_eq!(tokens[15].token_type, TokenType::SlashEqual);
        assert_eq!(tokens[16].token_type, TokenType::PercentEqual);
        assert_eq!(tokens[17].token_type, TokenType::BitAndEqual);
        assert_eq!(tokens[18].token_type, TokenType::BitOrEqual);
        assert_eq!(tokens[19].token_type, TokenType::BitXorEqual);
        assert_eq!(tokens[20].token_type, TokenType::Increment);
        assert_eq!(tokens[21].token_type, TokenType::Decrement);
        assert_eq!(tokens[22].token_type, TokenType::Arrow);
        assert_eq!(tokens[23].token_type, TokenType::FatArrow);
        assert_eq!(tokens[24].token_type, TokenType::StarStar);
    }

    #[test]
    fn test_number_formats() {
        let tokens = lex("123 3.14 0b1010 0xFF 0o755").unwrap();

        assert_eq!(tokens[0].text, "123");
        assert_eq!(tokens[1].text, "3.14");
        assert_eq!(tokens[2].text, "0b1010");
        assert_eq!(tokens[3].text, "0xFF");
        assert_eq!(tokens[4].text, "0o755");
    }

    #[test]
    fn test_comments() {
        let tokens = lex(
            "let x = 1 // Kommentar\n /* Block */ let y = 2"
        )
        .unwrap();

        assert_eq!(tokens[0].token_type, TokenType::Keyword);
        assert_eq!(tokens[1].text, "x");
        assert_eq!(tokens[3].text, "1");
        assert_eq!(tokens[4].token_type, TokenType::Keyword);
        assert_eq!(tokens[5].text, "y");
        assert_eq!(tokens[7].text, "2");
    }

    #[test]
    fn test_strings_and_chars() {
        let tokens = lex(r#"print("Hallo\nWelt"); 'A'"#).unwrap();

        assert_eq!(tokens[0].token_type, TokenType::Keyword);
        assert_eq!(tokens[1].token_type, TokenType::LeftParen);
        assert_eq!(tokens[2].token_type, TokenType::String);
        assert_eq!(tokens[2].text, "Hallo\nWelt");
        assert_eq!(tokens[4].token_type, TokenType::Semicolon);
        assert_eq!(tokens[5].token_type, TokenType::Character);
        assert_eq!(tokens[5].text, "A");
    }

    #[test]
    fn test_extra_symbols() {
        let tokens = lex("@ # =>").unwrap();

        assert_eq!(tokens[0].token_type, TokenType::At);
        assert_eq!(tokens[1].token_type, TokenType::Hash);
        assert_eq!(tokens[2].token_type, TokenType::FatArrow);
    }    #[test]
    fn test_nexa_keywords() {
        let tokens = lex(
            "let var const static global int int64 string bool array"
        ).unwrap();

        for token in &tokens[..tokens.len() - 1] {
            assert_eq!(token.token_type, TokenType::Keyword);
        }
    }
}


pub mod parser;

pub use parser::*;
