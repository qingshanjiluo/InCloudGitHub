"""
敏感信息检测模块
"""
import re
from typing import List, Dict, Optional
from config import SENSITIVE_PATTERNS, EXCLUDED_EXTENSIONS, EXCLUDED_DIRS


class SecretDetector:
    """敏感信息检测器"""
    
    def __init__(self, patterns: List[str] = SENSITIVE_PATTERNS):
        """
        初始化检测器
        
        Args:
            patterns: 正则表达式模式列表
        """
        self.patterns = [re.compile(pattern) for pattern in patterns]
        self.excluded_extensions = EXCLUDED_EXTENSIONS
        self.excluded_dirs = EXCLUDED_DIRS
    
    def should_scan_file(self, file_path: str) -> bool:
        """
        判断文件是否应该被扫描
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否应该扫描
        """
        # 检查文件扩展名
        for ext in self.excluded_extensions:
            if file_path.lower().endswith(ext):
                return False
        
        # 检查目录
        path_parts = file_path.split('/')
        for excluded_dir in self.excluded_dirs:
            if excluded_dir in path_parts:
                return False
        
        return True
    
    def detect_secrets_in_text(self, text: str, file_path: str = "") -> List[Dict]:
        """
        在文本中检测敏感信息
        
        Args:
            text: 要检测的文本内容
            file_path: 文件路径（用于报告）
            
        Returns:
            检测到的敏感信息列表
        """
        if not text:
            return []
        
        findings = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            for pattern in self.patterns:
                matches = pattern.finditer(line)
                for match in matches:
                    # 提取匹配的密钥
                    secret = match.group(0)
                    
                    # 检查是否是注释或示例
                    if self._is_likely_example(line, secret):
                        continue
                    
                    findings.append({
                        'file_path': file_path,
                        'line_number': line_num,
                        'line_content': line.strip(),
                        'secret': secret,
                        'pattern': pattern.pattern,
                        'confidence': self._calculate_confidence(secret, line)
                    })
        
        return findings
    
    def _is_likely_example(self, line: str, secret: str) -> bool:
        """
        判断是否可能是示例代码
        
        Args:
            line: 代码行
            secret: 检测到的密钥
            
        Returns:
            是否可能是示例
        """
        line_lower = line.lower()
        
        # 检查是否包含示例相关的关键词
        example_keywords = [
            'example', 'sample', 'demo', 'test', 'placeholder',
            'your_api_key', 'your-api-key', 'xxx', 'yyy',
            'todo', 'replace', 'change_me', 'changeme'
        ]
        
        for keyword in example_keywords:
            if keyword in line_lower:
                return True
        
        # 检查密钥是否包含明显的占位符模式
        placeholder_patterns = [
            r'x{10,}',  # 多个x
            r'_+',      # 多个下划线
            r'\*{3,}',  # 多个星号
        ]
        
        for pattern in placeholder_patterns:
            if re.search(pattern, secret, re.IGNORECASE):
                return True
        
        return False
    
    def _calculate_confidence(self, secret: str, line: str) -> str:
        """
        计算置信度
        
        Args:
            secret: 检测到的密钥
            line: 代码行
            
        Returns:
            置信度等级 (high/medium/low)
        """
        # 高置信度：密钥格式完整且不在注释中
        if (secret.startswith('sk-') and len(secret) > 40 and 
            not line.strip().startswith('#') and 
            not line.strip().startswith('//')):
            return 'high'
        
        # 中等置信度：符合基本模式
        if len(secret) >= 30:
            return 'medium'
        
        # 低置信度
        return 'low'
    
    def filter_high_confidence(self, findings: List[Dict]) -> List[Dict]:
        """
        过滤出高置信度的发现
        
        Args:
            findings: 检测结果列表
            
        Returns:
            高置信度的结果
        """
        return [f for f in findings if f['confidence'] in ['high', 'medium']]
    
    def deduplicate_findings(self, findings: List[Dict]) -> List[Dict]:
        """
        去除重复的发现
        
        Args:
            findings: 检测结果列表
            
        Returns:
            去重后的结果
        """
        seen = set()
        unique_findings = []
        
        for finding in findings:
            # 使用secret和file_path作为唯一标识
            key = (finding['secret'], finding['file_path'])
            if key not in seen:
                seen.add(key)
                unique_findings.append(finding)
        
        return unique_findings
