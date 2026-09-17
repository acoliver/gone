//! Rust-aware tokenizer used by the clippy-allow policy (issue #4) and the
//! harness protocol-surface policy (issue #5).
//!
//! Scans source text while skipping comments, string/char/raw-string
//! literals, and lifetimes; tracks nested brackets inside attributes; then
//! matches `allow`/`expect` attributes that name a `clippy::` lint on the
//! sanitized attribute text. Ported from jefe's `clippy_policy` scanner.

/// Scan a source string and return the normalized text of every attribute
/// that suppresses a clippy lint via `allow` or `expect`.
#[must_use]
pub fn scan_source(source: &str) -> Vec<String> {
    let bytes: Vec<char> = source.chars().collect();
    let len = bytes.len();
    let mut index = 0usize;
    let mut found = Vec::new();
    while index < len {
        if starts_with(&bytes, index, "//") {
            index = skip_line_comment(&bytes, index);
        } else if starts_with(&bytes, index, "/*") {
            index = skip_block_comment(&bytes, index);
        } else {
            let raw_end = skip_raw_string(&bytes, index);
            if raw_end != index {
                index = raw_end;
            } else if bytes[index] == '"' {
                index = skip_string(&bytes, index);
            } else if bytes[index] == '\'' {
                index = skip_char_literal(&bytes, index);
            } else if bytes[index] == '#' {
                if let Some((attr, end)) = collect_attribute(&bytes, index) {
                    let normalized = sanitize(&attr);
                    if is_clippy_allow(&normalized) {
                        found.push(normalized);
                    }
                    index = end;
                } else {
                    index += 1;
                }
            } else {
                index += 1;
            }
        }
    }
    found
}

/// Return the source with comments and string/char/raw-string literals
/// replaced by a single space, leaving every other character in place. The
/// result is safe to token-scan: text that only *mentions* an identifier
/// (in docs or literals) is gone, while real code paths survive verbatim.
#[must_use]
pub fn strip_comments_and_literals(source: &str) -> String {
    let bytes: Vec<char> = source.chars().collect();
    let len = bytes.len();
    let mut index = 0usize;
    let mut out = String::with_capacity(source.len());
    while index < len {
        if starts_with(&bytes, index, "//") {
            out.push(' ');
            index = skip_line_comment(&bytes, index);
        } else if starts_with(&bytes, index, "/*") {
            out.push(' ');
            index = skip_block_comment(&bytes, index);
        } else {
            let raw_end = skip_raw_string(&bytes, index);
            if raw_end != index {
                out.push(' ');
                index = raw_end;
            } else if bytes[index] == '"' {
                out.push(' ');
                index = skip_string(&bytes, index);
            } else if bytes[index] == '\'' {
                out.push(' ');
                index = skip_char_literal(&bytes, index);
            } else {
                out.push(bytes[index]);
                index += 1;
            }
        }
    }
    out
}

/// Does `bytes[index..]` start with `needle`?
fn starts_with(bytes: &[char], index: usize, needle: &str) -> bool {
    needle
        .chars()
        .enumerate()
        .all(|(offset, expected)| bytes.get(index + offset) == Some(&expected))
}

fn skip_line_comment(bytes: &[char], index: usize) -> usize {
    let mut i = index + 2;
    while i < bytes.len() && bytes[i] != '\n' {
        i += 1;
    }
    if i < bytes.len() { i + 1 } else { bytes.len() }
}

fn skip_block_comment(bytes: &[char], index: usize) -> usize {
    let mut depth = 1i32;
    let mut i = index + 2;
    while i < bytes.len() && depth > 0 {
        if starts_with(bytes, i, "/*") {
            depth += 1;
            i += 2;
        } else if starts_with(bytes, i, "*/") {
            depth -= 1;
            i += 2;
        } else {
            i += 1;
        }
    }
    i
}

fn skip_string(bytes: &[char], index: usize) -> usize {
    let mut i = index + 1;
    while i < bytes.len() {
        if bytes[i] == '\\' {
            i += 2;
        } else if bytes[i] == '"' {
            return i + 1;
        } else {
            i += 1;
        }
    }
    i
}

/// Skip a char literal but not a lifetime: `'x'`/`'\x'` are literals, `'a`
/// without a closing quote is a lifetime and only the quote is consumed.
fn skip_char_literal(bytes: &[char], index: usize) -> usize {
    let mut cursor = index + 1;
    if cursor >= bytes.len() {
        return index + 1;
    }
    if bytes[cursor] == '\\' {
        cursor += 2;
    } else {
        cursor += 1;
    }
    if cursor < bytes.len() && bytes[cursor] == '\'' {
        cursor + 1
    } else {
        index + 1
    }
}

/// Skip a raw string `r"..."`/`r#"..."#`/`br...`. Returns `index` unchanged
/// when the bytes do not begin a raw string.
fn skip_raw_string(bytes: &[char], index: usize) -> usize {
    let start = index;
    let mut i = index;
    if starts_with(bytes, i, "br") {
        i += 2;
    } else if bytes.get(i) == Some(&'r') {
        i += 1;
    } else {
        return start;
    }
    let mut hashes = 0usize;
    while i < bytes.len() && bytes[i] == '#' {
        hashes += 1;
        i += 1;
    }
    if i >= bytes.len() || bytes[i] != '"' {
        return start;
    }
    let mut terminator: Vec<char> = vec!['"'];
    terminator.resize(hashes + 1, '#');
    let mut search = i + 1;
    while search + terminator.len() <= bytes.len() {
        if bytes[search..search + terminator.len()] == terminator[..] {
            return search + terminator.len();
        }
        search += 1;
    }
    bytes.len()
}

/// Collect a `#[...]`/`#![...]` attribute starting at `index` (which points
/// at `#`). Returns the attribute text and the index after its closing
/// bracket, or `None` when this is not an attribute.
fn collect_attribute(bytes: &[char], start: usize) -> Option<(String, usize)> {
    let len = bytes.len();
    let mut index = start + 1;
    while index < len && bytes[index].is_whitespace() {
        index += 1;
    }
    if index < len && bytes[index] == '!' {
        index += 1;
        while index < len && bytes[index].is_whitespace() {
            index += 1;
        }
    }
    if index >= len || bytes[index] != '[' {
        return None;
    }
    let mut depth = 1i32;
    index += 1;
    while index < len && depth > 0 {
        if starts_with(bytes, index, "//") {
            index = skip_line_comment(bytes, index);
        } else if starts_with(bytes, index, "/*") {
            index = skip_block_comment(bytes, index);
        } else {
            let raw_end = skip_raw_string(bytes, index);
            if raw_end != index {
                index = raw_end;
            } else if bytes[index] == '"' {
                index = skip_string(bytes, index);
            } else if bytes[index] == '\'' {
                index = skip_char_literal(bytes, index);
            } else if bytes[index] == '[' {
                depth += 1;
                index += 1;
            } else if bytes[index] == ']' {
                depth -= 1;
                index += 1;
            } else {
                index += 1;
            }
        }
    }
    if depth != 0 {
        return None;
    }
    let attr: String = bytes[start..index].iter().collect();
    Some((attr, index))
}

/// Strip comments and literals from attribute text and normalize whitespace,
/// so the suppression matcher sees only structural tokens.
fn sanitize(attr: &str) -> String {
    let bytes: Vec<char> = attr.chars().collect();
    let len = bytes.len();
    let mut index = 0usize;
    let mut out = String::new();
    while index < len {
        if starts_with(&bytes, index, "//") {
            out.push(' ');
            index = skip_line_comment(&bytes, index);
        } else if starts_with(&bytes, index, "/*") {
            out.push(' ');
            index = skip_block_comment(&bytes, index);
        } else {
            let raw_end = skip_raw_string(&bytes, index);
            if raw_end != index {
                out.push(' ');
                index = raw_end;
            } else if bytes[index] == '"' {
                out.push(' ');
                index = skip_string(&bytes, index);
            } else if bytes[index] == '\'' {
                out.push(' ');
                index = skip_char_literal(&bytes, index);
            } else {
                out.push(bytes[index]);
                index += 1;
            }
        }
    }
    out.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Match `allow(`/`expect(` whose argument list names a `clippy::` lint,
/// allowing an optional `r#` raw-identifier prefix and whitespace around
/// `::`.
fn is_clippy_allow(normalized: &str) -> bool {
    for keyword in ["allow", "expect"] {
        let mut search = 0usize;
        while let Some(rel) = normalized[search..].find(keyword) {
            let abs = search + rel;
            let prev = if abs == 0 {
                b'\0'
            } else {
                normalized.as_bytes()[abs - 1]
            };
            if is_ident_continue(prev) {
                search = abs + keyword.len();
                continue;
            }
            let mut after = abs + keyword.len();
            while after < normalized.len() && normalized.as_bytes()[after].is_ascii_whitespace() {
                after += 1;
            }
            if after < normalized.len() && normalized.as_bytes()[after] == b'(' {
                let rest = &normalized[after..];
                if clippy_path_before_close(rest) {
                    return true;
                }
            }
            search = abs + keyword.len();
        }
    }
    false
}

/// Within `rest` (starting at `(`), check whether `(r#)?clippy\s*::` appears
/// before the first `)`. Word boundaries are enforced so identifiers merely
/// containing `clippy` (e.g. `my_clippy::lint`) do not match.
fn clippy_path_before_close(rest: &str) -> bool {
    let bytes = rest.as_bytes();
    let len = bytes.len();
    let mut i = 0usize;
    while i < len {
        if bytes[i] == b')' {
            return false;
        }
        let mut j = i;
        if rest[j..].starts_with("r#") {
            j += 2;
        }
        if rest[j..].starts_with("clippy") && !(i > 0 && is_ident_continue(bytes[i - 1])) {
            j += "clippy".len();
            while j < len && bytes[j].is_ascii_whitespace() {
                j += 1;
            }
            if j + 1 < len && bytes[j] == b':' && bytes[j + 1] == b':' {
                return true;
            }
        }
        i += 1;
    }
    false
}

/// Is `b` a Rust identifier-continue byte (alphanumeric or `_`)?
pub(crate) const fn is_ident_continue(b: u8) -> bool {
    b.is_ascii_alphanumeric() || b == b'_'
}

/// Tests for the tokenizer: positives, negatives, and literal/comment
/// blindness required by the clippy-allow policy.
#[cfg(test)]
mod tests {
    use super::{scan_source, strip_comments_and_literals};

    fn flagged(source: &str) -> bool {
        !scan_source(source).is_empty()
    }

    #[test]
    fn real_clippy_allow_is_flagged() {
        assert!(flagged("#[allow(clippy::too_many_arguments)]\nfn f() {}\n"));
    }

    #[test]
    fn real_clippy_expect_is_flagged() {
        assert!(flagged("#[expect(clippy::too_many_lines)]\nfn f() {}\n"));
    }

    #[test]
    fn allow_in_line_comment_is_not_flagged() {
        assert!(!flagged(
            "// #[allow(clippy::too_many_arguments)]\nfn f() {}\n"
        ));
    }

    #[test]
    fn allow_in_block_comment_is_not_flagged() {
        assert!(!flagged("/* allow(clippy::all) */\nfn f() {}\n"));
    }

    #[test]
    fn allow_in_string_literal_is_not_flagged() {
        assert!(!flagged(
            "const S: &str = \"#[allow(clippy::too_many_arguments)]\";\nfn f() {}\n"
        ));
    }

    #[test]
    fn allow_in_raw_string_is_not_flagged() {
        assert!(!flagged(
            "const S: &str = r##\"#[allow(clippy::too_many_arguments)]\"##;\nfn f() {}\n"
        ));
    }

    #[test]
    fn allow_in_char_literal_is_not_flagged() {
        assert!(!flagged(
            "const C: char = '\"';\n#[allow(dead_code)]\nfn f() {}\n"
        ));
    }

    #[test]
    fn non_clippy_allow_is_not_flagged() {
        assert!(!flagged("#[allow(dead_code)]\nfn unused() {}\n"));
    }

    #[test]
    fn cfg_attr_without_clippy_is_not_flagged() {
        assert!(!flagged("#[cfg(all(unix, feature = \"x\"))]\nfn f() {}\n"));
    }

    #[test]
    fn string_bracket_does_not_end_attribute_scan() {
        let source = "let s = \"]\";\n#[allow(dead_code)]\nfn f() {}\n";
        assert!(!flagged(source));
    }

    #[test]
    fn lifetime_is_not_mistaken_for_char_literal() {
        let source =
            "fn g<'a>(x: &'a str) {}\nconst S: &str = \"#[allow(clippy::all)]\";\nfn f() {}\n";
        assert!(!flagged(source));
    }

    #[test]
    fn expect_with_reason_is_flagged() {
        assert!(flagged(
            "#[expect(clippy::result_large_err, reason = \"fine\")]\nfn f() {}\n"
        ));
    }

    #[test]
    fn allow_without_parenthesized_clippy_is_not_flagged() {
        assert!(!flagged("#[allow]\nfn f() {}\n"));
    }

    #[test]
    fn substring_clippy_identifiers_are_not_flagged() {
        // An allow of a non-clippy tool lint whose path merely contains the
        // word clippy must not trigger.
        assert!(!flagged("#[allow(my_clippy::fake)]\nfn f() {}\n"));
    }

    #[test]
    fn strip_keeps_code_and_drops_comment_and_literal_mentions() {
        let source = "// gone_sim\nuse gone_sim::World; /* gone_sim */\n\
                      const S: &str = \"gone_sim\";\n\
                      const R: &str = r#\"gone_sim\"#;\n\
                      fn f() {}\n";
        let stripped = strip_comments_and_literals(source);
        assert!(stripped.contains("use gone_sim::World;"));
        assert!(stripped.contains("fn f() {}"));
        assert_eq!(stripped.matches("gone_sim").count(), 1);
    }

    #[test]
    fn strip_handles_nested_block_comments_and_char_literals() {
        let source = "/* /* gone_sim */ still comment */\n\
                      const C: char = '\\'';\n\
                      const S: &str = \"gone_sim\";\n\
                      fn f() {}\n";
        let stripped = strip_comments_and_literals(source);
        assert_eq!(stripped.matches("gone_sim").count(), 0);
        assert!(stripped.contains("fn f() {}"));
    }

    #[test]
    fn strip_consumes_only_the_lifetime_quote() {
        let stripped = strip_comments_and_literals("fn g<'a>(x: &'a str) {}");
        assert_eq!(stripped, "fn g< a>(x: & a str) {}");
    }
}
