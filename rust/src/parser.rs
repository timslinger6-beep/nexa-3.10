use crate::{Lexer, LexerError, Token, TokenType};

#[derive(Debug, Clone, PartialEq)]
pub enum Expression {
    Number(String),
    String(String),
    Character(String),
    Boolean(bool),
    Null,
    Array(Vec<Expression>),
    Variable(String),
    Index {
        target: Box<Expression>,
        index: Box<Expression>,
    },
    Member {
        target: Box<Expression>,
        member: String,
    },
    Unary {
        operator: TokenType,
        operand: Box<Expression>,
    },
    Binary {
        left: Box<Expression>,
        operator: TokenType,
        right: Box<Expression>,
    },
    Call {
        name: String,
        arguments: Vec<Expression>,
    },
    MethodCall {
        target: Box<Expression>,
        name: String,
        arguments: Vec<Expression>,
    },
    New {
        type_name: String,
        arguments: Vec<Expression>,
    },
}

#[derive(Debug, Clone, PartialEq)]
pub enum Statement {
    Expression(Expression),

    Print(Expression),

    VariableDeclaration {
        name: String,
        variable_type: String,
        expression: Expression,
    },

    Assignment {
        name: String,
        expression: Expression,
    },

    IndexAssignment {
        target: Expression,
        index: Expression,
        expression: Expression,
    },

    MemberAssignment {
        target: Expression,
        member: String,
        expression: Expression,
    },

    If {
        condition: Expression,
        then_branch: Vec<Statement>,
        else_branch: Option<Vec<Statement>>,
    },

    While {
        condition: Expression,
        body: Vec<Statement>,
    },

    DoWhile {
        body: Vec<Statement>,
        condition: Expression,
    },

    Switch {
        expression: Expression,
        cases: Vec<(Vec<Expression>, Vec<Statement>)>,
        default_body: Option<Vec<Statement>>,
    },

    Enum {
        name: String,
        members: Vec<String>,
    },

    For {
        initializer: Option<Box<Statement>>,
        condition: Option<Expression>,
        increment: Option<Box<Statement>>,
        body: Vec<Statement>,
    },

    Break,

    Continue,

    Return(Option<Expression>),

    Function {
        name: String,
        parameters: Vec<String>,
        body: Vec<Statement>,
    },

    Class {
        name: String,
        fields: Vec<(String, String)>,
        methods: Vec<Statement>,
        superclass_name: Option<String>,
    },

    Struct {
        name: String,
        fields: Vec<(String, String)>,
    },

    Import(String),

    Try {
        try_body: Vec<Statement>,
        catch_variable: Option<String>,
        catch_body: Vec<Statement>,
    },
}

#[derive(Debug, Clone, PartialEq)]
pub struct Program {
    pub statements: Vec<Statement>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ParserError {
    pub message: String,
    pub position: usize,
}

pub struct Parser {
    tokens: Vec<Token>,
    current: usize,
}

impl Parser {
    pub fn new(source: &str) -> Result<Self, LexerError> {
        let mut lexer = Lexer::new(source);
        let tokens = lexer.tokenize()?;

        Ok(Self {
            tokens,
            current: 0,
        })
    }

    pub fn parse(&mut self) -> Result<Program, ParserError> {
        let mut statements = Vec::new();

        while !self.is_at_end() {
            statements.push(self.parse_statement()?);
        }

        Ok(Program { statements })
    }

    fn parse_statement(&mut self) -> Result<Statement, ParserError> {
        if self.check_keyword("print") {
            return self.parse_print();
        }

        if self.check_keyword("let") {
            return self.parse_variable_declaration("auto");
        }

        if self.check_keyword("var") {
            return self.parse_variable_declaration("auto");
        }

        if self.check_keyword("const") {
            return self.parse_variable_declaration("const");
        }

        if self.check_keyword("if") {
            return self.parse_if();
        }

        if self.check_keyword("while") {
            return self.parse_while();
        }

        if self.check_keyword("do") {
            return self.parse_do_while();
        }

        if self.check_keyword("for") {
            return self.parse_for();
        }

        if self.check_keyword("break") {
            self.advance();
            self.consume(TokenType::Semicolon, "Expected ';' after break.")?;
            return Ok(Statement::Break);
        }

        if self.check_keyword("continue") {
            self.advance();
            self.consume(TokenType::Semicolon, "Expected ';' after continue.")?;
            return Ok(Statement::Continue);
        }

        if self.check_keyword("return") {
            return self.parse_return();
        }

        if self.check_keyword("function") || self.check_keyword("fn") {
            return self.parse_function();
        }

        if self.check_keyword("import") {
            return self.parse_import();
        }

        if self.check_keyword("struct") {
            return self.parse_struct();
        }

        if self.check_keyword("enum") {
            return self.parse_enum();
        }

        self.parse_expression_statement()
    }

    fn parse_print(&mut self) -> Result<Statement, ParserError> {
        self.advance();

        let expression = self.parse_expression()?;

        self.consume(
            TokenType::Semicolon,
            "Expected ';' after print expression.",
        )?;

        Ok(Statement::Print(expression))
    }

    fn parse_variable_declaration(
        &mut self,
        variable_type: &str,
    ) -> Result<Statement, ParserError> {
        self.advance();

        let name = self.consume_name("Expected variable name.")?;

        let expression = if self.match_token(TokenType::Equal) {
            self.parse_expression()?
        } else {
            Expression::Null
        };

        self.consume(
            TokenType::Semicolon,
            "Expected ';' after variable declaration.",
        )?;

        Ok(Statement::VariableDeclaration {
            name,
            variable_type: variable_type.to_string(),
            expression,
        })
    }

    fn parse_if(&mut self) -> Result<Statement, ParserError> {
        self.advance();

        self.consume(TokenType::LeftParen, "Expected '(' after if.")?;
        let condition = self.parse_expression()?;
        self.consume(TokenType::RightParen, "Expected ')' after condition.")?;

        let then_branch = self.parse_block()?;

        let else_branch = if self.check_keyword("else") {
            self.advance();

            if self.check_keyword("if") {
                Some(vec![self.parse_if()?])
            } else {
                Some(self.parse_block()?)
            }
        } else {
            None
        };

        Ok(Statement::If {
            condition,
            then_branch,
            else_branch,
        })
    }

    fn parse_while(&mut self) -> Result<Statement, ParserError> {
        self.advance();

        self.consume(TokenType::LeftParen, "Expected '(' after while.")?;
        let condition = self.parse_expression()?;
        self.consume(TokenType::RightParen, "Expected ')' after condition.")?;

        let body = self.parse_block()?;

        Ok(Statement::While { condition, body })
    }

    fn parse_do_while(&mut self) -> Result<Statement, ParserError> {
        self.advance();

        let body = self.parse_block()?;

        self.consume_keyword("while", "Expected 'while' after do block.")?;

        self.consume(TokenType::LeftParen, "Expected '(' after while.")?;
        let condition = self.parse_expression()?;
        self.consume(TokenType::RightParen, "Expected ')' after condition.")?;
        self.consume(TokenType::Semicolon, "Expected ';' after do-while.")?;

        Ok(Statement::DoWhile { body, condition })
    }

    fn parse_for(&mut self) -> Result<Statement, ParserError> {
        self.advance();

        self.consume(TokenType::LeftParen, "Expected '(' after for.")?;

        let initializer = if self.check(TokenType::Semicolon) {
            None
        } else {
            Some(Box::new(self.parse_for_header_statement()?))
        };

        self.consume(TokenType::Semicolon, "Expected ';' after for initializer.")?;

        let condition = if self.check(TokenType::Semicolon) {
            None
        } else {
            Some(self.parse_expression()?)
        };

        self.consume(TokenType::Semicolon, "Expected ';' after for condition.")?;

        let increment = if self.check(TokenType::RightParen) {
            None
        } else {
            Some(Box::new(self.parse_for_header_statement()?))
        };

        self.consume(TokenType::RightParen, "Expected ')' after for clauses.")?;

        let body = self.parse_block()?;

        Ok(Statement::For {
            initializer,
            condition,
            increment,
            body,
        })
    }

    fn parse_for_header_statement(&mut self) -> Result<Statement, ParserError> {
        if self.check_keyword("let") {
            return self.parse_variable_declaration_without_semicolon("auto");
        }

        if self.check_keyword("var") {
            return self.parse_variable_declaration_without_semicolon("auto");
        }

        self.parse_assignment_without_semicolon()
    }

    fn parse_variable_declaration_without_semicolon(
        &mut self,
        variable_type: &str,
    ) -> Result<Statement, ParserError> {
        self.advance();

        let name = self.consume_name("Expected variable name.")?;

        let expression = if self.match_token(TokenType::Equal) {
            self.parse_expression()?
        } else {
            Expression::Null
        };

        Ok(Statement::VariableDeclaration {
            name,
            variable_type: variable_type.to_string(),
            expression,
        })
    }

    fn parse_assignment_without_semicolon(&mut self) -> Result<Statement, ParserError> {
        let name = self.consume_name("Expected assignment target.")?;

        self.consume(TokenType::Equal, "Expected '=' in assignment.")?;

        let expression = self.parse_expression()?;

        Ok(Statement::Assignment { name, expression })
    }

    fn parse_return(&mut self) -> Result<Statement, ParserError> {
        self.advance();

        if self.check(TokenType::Semicolon) {
            self.advance();
            return Ok(Statement::Return(None));
        }

        let expression = self.parse_expression()?;

        self.consume(TokenType::Semicolon, "Expected ';' after return.")?;

        Ok(Statement::Return(Some(expression)))
    }

    fn parse_function(&mut self) -> Result<Statement, ParserError> {
        self.advance();

        let name = self.consume_name("Expected function name.")?;

        self.consume(TokenType::LeftParen, "Expected '(' after function name.")?;

        let mut parameters = Vec::new();

        if !self.check(TokenType::RightParen) {
            loop {
                parameters.push(self.consume_name("Expected parameter name.")?);

                if !self.match_token(TokenType::Comma) {
                    break;
                }
            }
        }

        self.consume(TokenType::RightParen, "Expected ')' after parameters.")?;

        if self.match_token(TokenType::Arrow) {
            self.consume_name("Expected return type after '->'.")?;
        }

        let body = self.parse_block()?;

        Ok(Statement::Function {
            name,
            parameters,
            body,
        })
    }

    fn parse_import(&mut self) -> Result<Statement, ParserError> {
        self.advance();

        let token_text = self.advance().text.clone();

        if self.previous().token_type != TokenType::String {
            return Err(self.error("Expected string after import."));
        }

        self.consume(TokenType::Semicolon, "Expected ';' after import.")?;

        Ok(Statement::Import(token_text))
    }

    fn parse_struct(&mut self) -> Result<Statement, ParserError> {
        self.advance();

        let name = self.consume_name("Expected struct name.")?;

        self.consume(TokenType::LeftBrace, "Expected '{' after struct name.")?;

        let mut fields = Vec::new();

        while !self.check(TokenType::RightBrace) && !self.is_at_end() {
            let field_type = self.consume_name("Expected field type.")?;

            let mut final_type = field_type.clone();

            if self.match_token(TokenType::LeftBracket) {
                self.consume(
                    TokenType::RightBracket,
                    "Expected ']' in array type.",
                )?;
                final_type.push_str("[]");
            }

            let field_name = self.consume_name("Expected field name.")?;

            self.consume(TokenType::Semicolon, "Expected ';' after field.")?;

            fields.push((field_name, final_type));
        }

        self.consume(TokenType::RightBrace, "Expected '}' after struct.")?;

        self.match_token(TokenType::Semicolon);

        Ok(Statement::Struct { name, fields })
    }

    fn parse_enum(&mut self) -> Result<Statement, ParserError> {
        self.advance();

        let name = self.consume_name("Expected enum name.")?;

        self.consume(TokenType::LeftBrace, "Expected '{' after enum name.")?;

        let mut members = Vec::new();

        while !self.check(TokenType::RightBrace) && !self.is_at_end() {
            members.push(self.consume_name("Expected enum member.")?);

            if !self.match_token(TokenType::Comma) {
                break;
            }
        }

        self.consume(TokenType::RightBrace, "Expected '}' after enum.")?;

        self.match_token(TokenType::Semicolon);

        Ok(Statement::Enum { name, members })
    }

    fn parse_expression_statement(&mut self) -> Result<Statement, ParserError> {
        let expression = self.parse_expression()?;

        self.consume(
            TokenType::Semicolon,
            "Expected ';' after expression.",
        )?;

        Ok(Statement::Expression(expression))
    }

    fn parse_expression(&mut self) -> Result<Expression, ParserError> {
        self.parse_ternary()
    }

    fn parse_ternary(&mut self) -> Result<Expression, ParserError> {
        let condition = self.parse_logical_or()?;

        if self.match_token(TokenType::Question) {
            let true_value = self.parse_expression()?;

            self.consume(TokenType::Colon, "Expected ':' in ternary expression.")?;

            let false_value = self.parse_expression()?;

            return Ok(Expression::Call {
                name: "__nexa_ternary".to_string(),
                arguments: vec![condition, true_value, false_value],
            });
        }

        Ok(condition)
    }

    fn parse_logical_or(&mut self) -> Result<Expression, ParserError> {
        let mut expression = self.parse_logical_and()?;

        while self.match_token(TokenType::LogicalOr) {
            let operator = self.previous().token_type.clone();
            let right = self.parse_logical_and()?;

            expression = Expression::Binary {
                left: Box::new(expression),
                operator,
                right: Box::new(right),
            };
        }

        Ok(expression)
    }

    fn parse_logical_and(&mut self) -> Result<Expression, ParserError> {
        let mut expression = self.parse_comparison()?;

        while self.match_token(TokenType::LogicalAnd) {
            let operator = self.previous().token_type.clone();
            let right = self.parse_comparison()?;

            expression = Expression::Binary {
                left: Box::new(expression),
                operator,
                right: Box::new(right),
            };
        }

        Ok(expression)
    }

    fn parse_comparison(&mut self) -> Result<Expression, ParserError> {
        let mut expression = self.parse_bit_or()?;

        while self.match_any(&[
            TokenType::EqualEqual,
            TokenType::NotEqual,
            TokenType::Less,
            TokenType::Greater,
            TokenType::LessEqual,
            TokenType::GreaterEqual,
        ]) {
            let operator = self.previous().token_type.clone();
            let right = self.parse_bit_or()?;

            expression = Expression::Binary {
                left: Box::new(expression),
                operator,
                right: Box::new(right),
            };
        }

        Ok(expression)
    }

    fn parse_bit_or(&mut self) -> Result<Expression, ParserError> {
        let mut expression = self.parse_bit_xor()?;

        while self.match_token(TokenType::BitOr) {
            let operator = self.previous().token_type.clone();
            let right = self.parse_bit_xor()?;

            expression = Expression::Binary {
                left: Box::new(expression),
                operator,
                right: Box::new(right),
            };
        }

        Ok(expression)
    }

    fn parse_bit_xor(&mut self) -> Result<Expression, ParserError> {
        let mut expression = self.parse_bit_and()?;

        while self.match_token(TokenType::BitXor) {
            let operator = self.previous().token_type.clone();
            let right = self.parse_bit_and()?;

            expression = Expression::Binary {
                left: Box::new(expression),
                operator,
                right: Box::new(right),
            };
        }

        Ok(expression)
    }

    fn parse_bit_and(&mut self) -> Result<Expression, ParserError> {
        let mut expression = self.parse_shift()?;

        while self.match_token(TokenType::BitAnd) {
            let operator = self.previous().token_type.clone();
            let right = self.parse_shift()?;

            expression = Expression::Binary {
                left: Box::new(expression),
                operator,
                right: Box::new(right),
            };
        }

        Ok(expression)
    }

    fn parse_shift(&mut self) -> Result<Expression, ParserError> {
        let mut expression = self.parse_addition()?;

        while self.match_any(&[
            TokenType::ShiftLeft,
            TokenType::ShiftRight,
        ]) {
            let operator = self.previous().token_type.clone();
            let right = self.parse_addition()?;

            expression = Expression::Binary {
                left: Box::new(expression),
                operator,
                right: Box::new(right),
            };
        }

        Ok(expression)
    }

    fn parse_addition(&mut self) -> Result<Expression, ParserError> {
        let mut expression = self.parse_multiplication()?;

        while self.match_any(&[
            TokenType::Plus,
            TokenType::Minus,
        ]) {
            let operator = self.previous().token_type.clone();
            let right = self.parse_multiplication()?;

            expression = Expression::Binary {
                left: Box::new(expression),
                operator,
                right: Box::new(right),
            };
        }

        Ok(expression)
    }

    fn parse_multiplication(&mut self) -> Result<Expression, ParserError> {
        let mut expression = self.parse_power()?;

        while self.match_any(&[
            TokenType::Star,
            TokenType::Slash,
            TokenType::Percent,
        ]) {
            let operator = self.previous().token_type.clone();
            let right = self.parse_power()?;

            expression = Expression::Binary {
                left: Box::new(expression),
                operator,
                right: Box::new(right),
            };
        }

        Ok(expression)
    }

    fn parse_power(&mut self) -> Result<Expression, ParserError> {
        let mut expression = self.parse_unary()?;

        while self.match_any(&[
            TokenType::StarStar,
            TokenType::Caret,
        ]) {
            let operator = self.previous().token_type.clone();
            let right = self.parse_unary()?;

            expression = Expression::Binary {
                left: Box::new(expression),
                operator,
                right: Box::new(right),
            };
        }

        Ok(expression)
    }

    fn parse_unary(&mut self) -> Result<Expression, ParserError> {
        if self.match_any(&[
            TokenType::Minus,
            TokenType::LogicalNot,
            TokenType::BitNot,
            TokenType::Plus,
        ]) {
            let operator = self.previous().token_type.clone();
            let operand = self.parse_unary()?;

            return Ok(Expression::Unary {
                operator,
                operand: Box::new(operand),
            });
        }

        self.parse_postfix()
    }

    fn parse_postfix(&mut self) -> Result<Expression, ParserError> {
        let mut expression = self.parse_primary()?;

        loop {
            if self.match_token(TokenType::LeftBracket) {
                let index = self.parse_expression()?;

                self.consume(TokenType::RightBracket, "Expected ']' after index.")?;

                expression = Expression::Index {
                    target: Box::new(expression),
                    index: Box::new(index),
                };

                continue;
            }

            if self.match_token(TokenType::Dot) {
                let member = self.consume_name("Expected member name after '.'.")?;

                if self.match_token(TokenType::LeftParen) {
                    let arguments = self.parse_arguments_after_open_paren()?;

                    expression = Expression::MethodCall {
                        target: Box::new(expression),
                        name: member,
                        arguments,
                    };
                } else {
                    expression = Expression::Member {
                        target: Box::new(expression),
                        member,
                    };
                }

                continue;
            }

            break;
        }

        Ok(expression)
    }

    fn parse_primary(&mut self) -> Result<Expression, ParserError> {
        if self.match_token(TokenType::Number) {
            return Ok(Expression::Number(self.previous().text.clone()));
        }

        if self.match_token(TokenType::String) {
            return Ok(Expression::String(self.previous().text.clone()));
        }

        if self.match_token(TokenType::Character) {
            return Ok(Expression::Character(self.previous().text.clone()));
        }

        if self.check_keyword("true") {
            self.advance();
            return Ok(Expression::Boolean(true));
        }

        if self.check_keyword("false") {
            self.advance();
            return Ok(Expression::Boolean(false));
        }

        if self.check_keyword("null") || self.check_keyword("none") {
            self.advance();
            return Ok(Expression::Null);
        }

        if self.check_keyword("new") {
            return self.parse_new();
        }

        if self.match_token(TokenType::LeftParen) {
            let expression = self.parse_expression()?;
            self.consume(TokenType::RightParen, "Expected ')' after expression.")?;
            return Ok(expression);
        }

        if self.match_token(TokenType::LeftBracket) {
            return self.parse_array();
        }

        if self.check_identifier_like() {
            let name = self.consume_name("Expected identifier.")?;

            if self.match_token(TokenType::LeftParen) {
                let arguments = self.parse_arguments_after_open_paren()?;

                return Ok(Expression::Call { name, arguments });
            }

            return Ok(Expression::Variable(name));
        }

        Err(self.error("Expected expression."))
    }

    fn parse_new(&mut self) -> Result<Expression, ParserError> {
        self.advance();

        let type_name = self.consume_name("Expected type name after new.")?;

        self.consume(TokenType::LeftParen, "Expected '(' after type name.")?;

        let arguments = self.parse_arguments_after_open_paren()?;

        Ok(Expression::New {
            type_name,
            arguments,
        })
    }

    fn parse_array(&mut self) -> Result<Expression, ParserError> {
        let mut elements = Vec::new();

        if !self.check(TokenType::RightBracket) {
            loop {
                elements.push(self.parse_expression()?);

                if !self.match_token(TokenType::Comma) {
                    break;
                }
            }
        }

        self.consume(TokenType::RightBracket, "Expected ']' after array.")?;

        Ok(Expression::Array(elements))
    }

    fn parse_arguments_after_open_paren(&mut self) -> Result<Vec<Expression>, ParserError> {
        let mut arguments = Vec::new();

        if !self.check(TokenType::RightParen) {
            loop {
                arguments.push(self.parse_expression()?);

                if !self.match_token(TokenType::Comma) {
                    break;
                }
            }
        }

        self.consume(TokenType::RightParen, "Expected ')' after arguments.")?;

        Ok(arguments)
    }

    fn parse_block(&mut self) -> Result<Vec<Statement>, ParserError> {
        self.consume(TokenType::LeftBrace, "Expected '{'.")?;

        let mut statements = Vec::new();

        while !self.check(TokenType::RightBrace) && !self.is_at_end() {
            statements.push(self.parse_statement()?);
        }

        self.consume(TokenType::RightBrace, "Expected '}'.")?;

        Ok(statements)
    }

    fn check(&self, token_type: TokenType) -> bool {
        if self.is_at_end() {
            return token_type == TokenType::Eof;
        }

        self.peek().token_type == token_type
    }

    fn check_keyword(&self, keyword: &str) -> bool {
        self.peek().token_type == TokenType::Keyword
            && self.peek().text == keyword
    }

    fn check_identifier_like(&self) -> bool {
        matches!(
            self.peek().token_type,
            TokenType::Identifier | TokenType::Keyword
        )
    }

    fn consume_name(&mut self, message: &str) -> Result<String, ParserError> {
        if self.check_identifier_like() {
            return Ok(self.advance().text.clone());
        }

        Err(self.error(message))
    }

    fn consume(
        &mut self,
        token_type: TokenType,
        message: &str,
    ) -> Result<Token, ParserError> {
        if self.check(token_type.clone()) {
            return Ok(self.advance().clone());
        }

        Err(self.error(message))
    }

    fn consume_keyword(
        &mut self,
        keyword: &str,
        message: &str,
    ) -> Result<Token, ParserError> {
        if self.check_keyword(keyword) {
            return Ok(self.advance().clone());
        }

        Err(self.error(message))
    }

    fn match_token(&mut self, token_type: TokenType) -> bool {
        if self.check(token_type) {
            self.advance();
            return true;
        }

        false
    }

    fn match_any(&mut self, token_types: &[TokenType]) -> bool {
        for token_type in token_types {
            if self.check(token_type.clone()) {
                self.advance();
                return true;
            }
        }

        false
    }

    fn advance(&mut self) -> &Token {
        if !self.is_at_end() {
            self.current += 1;
        }

        self.previous()
    }

    fn peek(&self) -> &Token {
        &self.tokens[self.current]
    }

    fn previous(&self) -> &Token {
        &self.tokens[self.current - 1]
    }

    fn is_at_end(&self) -> bool {
        self.peek().token_type == TokenType::Eof
    }

    fn error(&self, message: &str) -> ParserError {
        ParserError {
            message: message.to_string(),
            position: self.peek().position,
        }
    }
}

