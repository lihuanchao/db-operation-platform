import hashlib
import re

import sqlparse


class SqlFingerprintService:
    COMMENT_BLOCK_PATTERN = re.compile(r'/\*.*?\*/', re.DOTALL)
    COMMENT_LINE_PATTERN = re.compile(r'--.*?(?:\r\n|\r|\n|$)')
    SINGLE_QUOTE_PATTERN = re.compile(r"'(?:''|[^'])*'")
    DOUBLE_QUOTE_PATTERN = re.compile(r'"(?:\\"|[^"])*"')
    NUMBER_PATTERN = re.compile(r'\b\d+(?:\.\d+)?\b')
    IN_LIST_PATTERN = re.compile(r'\bIN\s*\((?:\s*\?\s*,?)+\)', re.IGNORECASE)
    WHITESPACE_PATTERN = re.compile(r'\s+')

    @classmethod
    def fingerprint(cls, sql_text):
        normalized = cls.normalize(sql_text)
        return normalized, cls.fingerprint_hash(normalized)

    @classmethod
    def normalize(cls, sql_text):
        raw = (sql_text or '').strip()
        if not raw:
            return ''

        no_comments = cls.COMMENT_BLOCK_PATTERN.sub(' ', raw)
        no_comments = cls.COMMENT_LINE_PATTERN.sub(' ', no_comments)
        formatted = sqlparse.format(
            no_comments,
            keyword_case='upper',
            strip_comments=True,
            strip_whitespace=True,
            reindent=False,
        )
        masked = cls.SINGLE_QUOTE_PATTERN.sub('?', formatted)
        masked = cls.DOUBLE_QUOTE_PATTERN.sub('?', masked)
        masked = cls.NUMBER_PATTERN.sub('?', masked)
        masked = cls.IN_LIST_PATTERN.sub('IN (?)', masked)
        normalized = cls.WHITESPACE_PATTERN.sub(' ', masked).strip()
        return normalized

    @staticmethod
    def fingerprint_hash(normalized_sql):
        payload = (normalized_sql or '').encode('utf-8')
        return hashlib.sha256(payload).hexdigest()
